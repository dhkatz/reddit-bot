import importlib
import logging
import sys
from collections import deque
from logging.handlers import RotatingFileHandler

import praw
import praw.models as models
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

from .scheduler import *
from .validator import *


class Reddit:
    SUBREDDITS = 'doctorjewtest'

    __slots__ = [
        'config', '_username', '_password', '_client_id', '_client_secret', '_user_agent', '_checked_comments',
        '_checked_posts', '_post_checks', '_comment_checks', '_report_checks', 'domains', 'reddit',
        'scheduler', 'validators', 'extensions', 'log'
    ]

    def __init__(self, config: str = None):
        path = config
        config = configparser.ConfigParser()
        config.read(path if path else os.path.join(os.path.dirname(__file__), 'config.ini'))

        self.config = config
        self._username = config.get('reddit', 'username')
        self._password = config.get('reddit', 'password')
        self._client_id = config.get('reddit', 'client_id')
        self._client_secret = config.get('reddit', 'client_secret')
        self._user_agent = config.get('reddit', 'user_agent')
        self._checked_comments = deque(maxlen=100)
        self._checked_posts = deque(maxlen=100)
        self._post_checks = []
        self._comment_checks = []
        self._report_checks = []

        self.domains = dict(config.items('domains'))
        self.reddit = praw.Reddit(username=self._username, password=self._password, client_id=self._client_id,
                                  client_secret=self._client_secret, user_agent=self._user_agent)

        executors = dict(default=ThreadPoolExecutor(20), processpool=ProcessPoolExecutor())
        job_defaults = dict(coalesce=True, max_instances=4)
        self.scheduler = SmartScheduler(BlockingScheduler(executors=executors, job_defaults=job_defaults))
        self.validators = {}
        self.extensions = {'COMMENT': [], 'SUBMISSION': []}

        self.log = set_logger(self.config.get('general', 'log_level'))

        if path:
            self.log.debug(f'[Core] Loaded custom configuration file from {path}')

    def run(self):
        self.setup()
        self.log.info(f'[Core] Logged in as {self.reddit.user.me()}')

        self.scheduler.register_job("Posts", 30, self.process_submissions, self.log)
        self.scheduler.register_job("Comments", 10, self.process_comments, self.log)
        self.scheduler.start()

    def setup(self):
        for _, validator in self.config.items('validators'):
            if not validator:
                continue

            try:
                self.load_validator(validator)
            except ImportError as error:
                self.log.error(f'[Core] Unable to load validator: {validator}! (Error: {error})')
            else:
                self.log.debug(f'[Core] Loaded validator: {validator}!')

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
        for submission in self.reddit.subreddit(self.SUBREDDITS).mod.unmoderated():
            if submission.id in self._checked_posts:
                continue
            self._checked_posts.append(submission.id)

            approved = False
            for validator in self.extensions['SUBMISSION']:
                validator.dlog('Checking submission...')
                action, rule = validator.validate(submission)
                if action == Action.REMOVE:
                    validator.dlog('Submission failed check!')
                    self.remove_submission(submission, rule)
                    break
                elif action == Action.MANUAL:
                    validator.dlog('Leaving for manual approval.')
                    break
                elif action == Action.PASS:
                    validator.dlog('Ignoring submission.')
                else:
                    approved = True
                validator.dlog('Submission passed check!')
            else:
                if approved:  # In case no validators explicitly approve, they might all pass!
                    self.approve_submission(submission)

    def approve_submission(self, submission: models.Submission):
        self.log.debug(f'[Core] Submission would have been approved!')
        submission.mod.approve()

    def remove_submission(self, submission: models.Submission, rule: Rule):
        self.log.debug(f'[Core] Submission would have been removed!')
        submission.reply(str(rule)).mod.distinguish(sticky=False)
        submission.mod.remove()

    def process_comments(self):
        for comment in self.reddit.subreddit(self.SUBREDDITS).comments(limit=100):
            if comment.id in self._checked_comments or comment.submission.archived:
                break  # We don't want to revalidate comments or go too old
            self._checked_comments.append(comment.id)

            approved = False
            for validator in self.extensions['COMMENT']:
                validator.dlog('Checking comment...')
                action, rule = validator.validate(comment)
                if action == Action.REMOVE:
                    validator.dlog('Comment failed check!')
                    self.remove_comment(comment, rule)
                    break
                elif action == Action.MANUAL:
                    validator.dlog('Leaving for manual approval.')
                    break
                elif action == Action.PASS:
                    validator.dlog('Ignoring comment.')
                else:
                    approved = True
                validator.dlog('Comment passed check!')
            else:
                if approved:  # In case no validators explicitly approve, they might all pass!
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

    fh = RotatingFileHandler(filename='data/reddit.log', maxBytes=1024 * 5, backupCount=2, encoding='utf-8',
                             mode='w')
    fh.setFormatter(log_format)
    fh.setLevel(level)
    logger.addHandler(fh)

    return logger
