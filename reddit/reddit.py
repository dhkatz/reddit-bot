import importlib
import logging
import sys
from collections import deque
from logging.handlers import RotatingFileHandler

import praw
import praw.models as models
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

from .database import *
from .enums import Reason
from .scheduler import *
from .validator import *


class Reddit:
    SUBREDDITS = 'doctorjewtest'

    def __init__(self, config: str=None):
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

        self.database = Database()
        self.domains = dict(config.items('domains'))
        self.reddit = praw.Reddit(username=self._username, password=self._password, client_id=self._client_id,
                                  client_secret=self._client_secret, user_agent=self._user_agent)

        executors = dict(default=ThreadPoolExecutor(20), processpool=ProcessPoolExecutor(5))
        job_defaults = dict(coalesce=True, max_instances=2)
        self.scheduler = SmartScheduler(BlockingScheduler(executors=executors, job_defaults=job_defaults))
        self.validators = {}
        self.extensions = {'COMMENT': [], 'SUBMISSION': []}

        self.log = set_logger()

    def run(self):
        self.setup()
        self.log.info(f'[Core] Logged in as {self.reddit.user.me()}')

        self.scheduler.register_job("Posts", 15, self.process_submissions)
        # self.scheduler.add_job(self.process_reports, 'interval', minutes=1)
        # self.scheduler.register_job("Comments", 10, self.process_comments)
        self.scheduler.start()

    def setup(self):
        for _, validators in self.config.items('validators'):
            if not validators:
                continue

            for validator in validators.split(','):
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
        if issubclass(type(validator), SubmissionValidator):
            self.extensions['SUBMISSION'].append(validator)
        elif issubclass(type(validator), CommentValidator):
            self.extensions['COMMENT'].append(validator)

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
            for validator in self.extensions['SUBMISSION']:
                self.log.info(f'[{validator.__class__.__name__}] Checking submission...')
                valid, reason = validator.validate(submission)
                if not valid:
                    self.log.info(f'[{validator.__class__.__name__}] Submission failed check!')
                    self.remove_submission(submission, reason)
                    break
                self.log.info(f'[{validator.__class__.__name__}] Submission passed check!')
            else:
                self.approve_submission(submission)

    def approve_submission(self, submission: models.Submission):
        self.log.info(f'[Core] Submission would have been approved!')
        submission.mod.approve()

    def remove_submission(self, submission: models.Submission, reason: Reason):
        self.log.info(f'[Core] Submission would have been removed!')
        submission.reply(str(reason)).mod.distinguish(sticky=False)
        submission.mod.remove()

    def process_comments(self):
        for comment in self.reddit.subreddit(self.SUBREDDITS).comments(limit=50):
            if comment.id in self._checked_comments or comment.submission.archived:
                continue
            self._checked_comments.append(comment.id)

            for validator in self.extensions['COMMENT']:
                if not validator.validate(comment):
                    comment.mod.remove()
                    continue


def set_logger():
    logger = logging.getLogger('reddit')
    logger.setLevel(logging.INFO)
    log_format = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(log_format)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    fh = RotatingFileHandler(filename='data/reddit.log', maxBytes=1024 * 5, backupCount=2, encoding='utf-8',
                             mode='w')
    fh.setFormatter(log_format)
    logger.addHandler(fh)

    return logger
