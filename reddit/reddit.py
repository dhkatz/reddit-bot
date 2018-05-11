import configparser
import importlib
import sys
import time
from logging.handlers import RotatingFileHandler

import praw
import praw.models as models
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

from .scheduler import *
from .validator import *


class Reddit:
    """Reddit bot designed to process submissions and comments on watched subreddits.

    Parameters
    ----------
    config_path : str
        Path to custom configuration file.

    Attributes
    ----------
    config: configparser.ConfigParser
        The configuration of the bot.
    log: logging.Logger
        Logger used for saving log files and debugging.
    reddit: praw.Reddit
        The PRAW instance used for interaction with Reddit.
    subreddits: praw.Subreddit
        Subreddit instance of watched subreddits
    scheduler: SmartScheduler
        Custom scheduler with misfire protection used for background tasks.
    domains: dict
        Known domains the validators may look out for.
    validators: dict
        Modules of the validators that every Comment and Submission are checked against.
    extensions: dict
        Contains the actually objects of every Validator
    start_time: float
        Time the bot started, epoch time.
    """

    __slots__ = [
        'config', '_post_checks', '_comment_checks', '_report_checks',
        'domains', 'reddit', 'scheduler', 'validators', 'extensions', 'log', 'start_time',
        '_comment_thread', '_submission_thread', 'subreddits', '_results'
    ]

    def __init__(self, config_path: str = None):
        path = config_path
        config_path = configparser.ConfigParser()
        config_path.read(path if path else os.path.join(os.path.dirname(__file__), 'config.ini'))

        self.config = config_path
        self.log = set_logger(self.config.get('logging', 'log_level'))

        info = dict(config_path.items('reddit'))
        self.reddit = praw.Reddit(
            username=info['username'], password=info['password'], client_id=info['client_id'],
            client_secret=info['client_secret'], user_agent=info['user_agent']
        )
        self.subreddits = self.reddit.subreddit(self.config.get('general', 'subreddits'))

        self.log.info(f'[Core] Logged in as {self.reddit.user.me()}')

        self.scheduler = SmartScheduler(BackgroundScheduler(
            executors=dict(default=ThreadPoolExecutor(20), processpool=ProcessPoolExecutor()),
            job_defaults=dict(coalesce=True, max_instances=4))
        )

        self.domains = dict(config_path.items('domains'))
        self.validators = {}
        self.extensions = {'COMMENT': [], 'SUBMISSION': []}

        self.start_time = time.time()

        if path:
            self.log.debug(f'[Core] Loaded custom configuration file from {path}')

        self._comment_thread = threading.Thread(target=self.process_comments, args=())
        self._submission_thread = threading.Thread(target=self.process_submissions, args=())
        self._post_checks = []
        self._comment_checks = []
        self._report_checks = []
        self._results = []

    def run(self):
        """Begin execution of all processing."""
        self._setup()

        self.scheduler.start()
        self._comment_thread.start()
        self._submission_thread.start()

    def _setup(self):
        for _, validator in self.config.items('validators'):
            if not validator:
                continue

            try:
                self.load_validator(validator)
            except ImportError as error:
                self.log.error(f'[Core] Unable to load validator: {validator}! (Error: {error})')
            else:
                self.log.info(f'[Core] Loaded validator: {validator}!')

    def load_validator(self, name):
        name = name + '.' + name.split('.')[1]
        if name in self.validators:
            return

        lib = importlib.import_module(name)
        if not hasattr(lib, 'setup'):
            del lib
            del sys.modules[name]
            raise ImportError('Extension does not have a setup function')

        lib.setup(self)
        self.validators[name] = lib

    def unload_validator(self, name):
        lib = self.validators.get(name)
        if lib is None:
            return

        lib_name = lib.__name__

        for extension_name, extension in self.extensions.copy().items():
            if lib_name == extension.__module__ or extension.__module__.startswith(lib_name + "."):
                self.remove_extension(extension_name)

        del lib
        del self.validators[name]
        del sys.modules[name]
        for module in list(sys.modules.keys()):
            if lib_name == module or module.startswith(lib_name + "."):
                del sys.modules[module]

    def add_extension(self, validator: Validator):
        if issubclass(type(validator), SubmissionValidator):  # Submission specific validators
            self.extensions['SUBMISSION'].append(validator)
        elif issubclass(type(validator), CommentValidator):  # Comment specific validators
            self.extensions['COMMENT'].append(validator)
        elif issubclass(type(validator), Validator):  # Generic validators run on both
            self.extensions['SUBMISSION'].append(validator)
            self.extensions['COMMENT'].append(validator)
        else:
            raise TypeError("Validator must be a subclass of either SubmissionValidator/CommentValidator or Validator!")

    def get_extension(self, name):
        return self.extensions.get(name)

    def remove_extension(self, name):
        extension = self.extensions.pop(name, None)
        if extension is None:
            return

        del extension

    def process_submissions(self):
        self.log.info(f'[Core] Beginning submission processing!')
        for submission in self.subreddits.stream.submissions():
            if submission.created_utc - self.start_time < 0:  # Ignore old (they get loaded initially sometimes)
                continue
            elif submission.removed:  # In case another bot got to it first!
                continue
            else:
                self.check_submission(submission)

    def check_submission(self, submission: models.Submission):
        approved, manual = False, False
        for validator in self.extensions['SUBMISSION']:
            validator.dlog('Checking submission...')
            action, rule = validator.validate(submission)
            if action == Action.REMOVE:
                validator.dlog('Submission failed check!')
                self.remove_submission(submission, rule)
                break
            elif action == Action.MANUAL:
                validator.dlog('Leaving for manual approval.')
                manual = True
            elif action == Action.PASS:
                validator.dlog('Ignoring submission.')
            else:
                approved = True
                validator.dlog('Submission passed check!')
        else:
            if approved and not manual:  # In case no validators explicitly approve, they might all pass!
                self.approve_submission(submission)
            elif manual:
                self.log.debug(f'[Core] Submission waiting for manual approval! {submission.permalink}')

    def approve_submission(self, submission: models.Submission):
        self.log.debug(f'[Core] Submission would have been approved! {submission.permalink}')
        submission.mod.approve()

    def remove_submission(self, submission: models.Submission, rule: Rule):
        self.log.debug(f'[Core] Submission would have been removed! {submission.permalink}')
        submission.reply(str(rule)).mod.distinguish(sticky=False)
        submission.mod.remove()

    def process_comments(self):
        self.log.info(f'[Core] Beginning comment processing!')
        for comment in self.subreddits.stream.comments():
            if comment.created_utc - self.start_time < 0:
                continue
            else:
                self.check_comment(comment)

    def check_comment(self, comment: models.Comment):
        if comment.submission.archived:
            return  # We don't want to revalidate comments or go too old

        approved, manual = False, True
        for validator in self.extensions['COMMENT']:
            validator.dlog('Checking comment...')
            action, rule = validator.validate(comment)
            if action == Action.REMOVE:
                validator.dlog('Comment failed check!')
                self.remove_comment(comment, rule)
                break
            elif action == Action.MANUAL:
                validator.dlog('Leaving for manual approval.')
                manual = True
            elif action == Action.PASS:
                validator.dlog('Ignoring comment.')
            else:
                approved = True
                validator.dlog('Comment passed check!')
        else:
            if approved and not manual:  # In case no validators explicitly approve, they might all pass!
                self.approve_comment(comment)

    def approve_comment(self, comment: Comment):
        self.log.debug(f'[Core] Comment would have been approved!')
        comment.mod.approve()

    def remove_comment(self, comment: Comment, rule: Rule):
        self.log.debug(f'[Core] Comment would have been removed!')
        if self.config.getboolean('general', 'comment_reason'):
            comment.reply(str(rule)).mod.distinguish(sticky=False)
        comment.mod.remove()


def set_logger(level: str):
    level = level.upper()

    logger = logging.getLogger('reddit')
    logger.setLevel(level)
    log_format = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(log_format)
    ch.setLevel(level)
    logger.addHandler(ch)

    fh = RotatingFileHandler(filename='data/reddit.log', maxBytes=1024 * 1024 * 10, backupCount=2, encoding='utf-8')
    fh.setFormatter(log_format)
    fh.setLevel(level)
    logger.addHandler(fh)

    return logger
