import configparser
import inspect
import os

from praw.models import Submission, Comment

from .enums import Valid


class Validator:
    __slots__ = ['_praw', 'config', 'reddit']

    def __init__(self, reddit):
        self._praw = reddit.reddit
        self.reddit = reddit
        self.config = configparser.ConfigParser()
        # Magic to dynamically load a file relative to the current class executing
        self.config.read(os.path.join(os.path.dirname(inspect.stack()[1][1]), 'config.ini'))
        self.reddit.scheduler.register_job(type(self).__name__, 15, self.process)

    def process(self):
        pass

    def dlog(self, message: str):
        """Log messages at the debug level. The validator name is prefixed automatically!"""
        self.reddit.log.debug(f'[{type(self).__name__}] ' + message)


class SubmissionValidator(Validator):
    def validate(self, submission: Submission) -> Valid:
        return True, None


class CommentValidator(Validator):
    def validate(self, comment: Comment) -> Valid:
        return True, None
