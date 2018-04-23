import configparser
import inspect
import os

from typing import Tuple

from praw.models import Submission, Comment

from .enums import Action, Rule


class Validator:
    __slots__ = ['_praw', 'config', 'reddit']

    def __init__(self, reddit):
        super().__init__()
        self._praw = reddit.reddit
        self.reddit = reddit
        self.config = configparser.ConfigParser()
        # Magic to dynamically load a file relative to the current class executing
        if os.path.isfile(os.path.join(os.path.dirname(inspect.stack()[1][1]), 'config.ini')):
            self.config.read(os.path.join(os.path.dirname(inspect.stack()[1][1]), 'config.ini'))
        self.reddit.scheduler.register_job(type(self).__name__, 15, self.process, self.reddit.log)

    def process(self):
        pass

    def dlog(self, message: str):
        """Log messages at the debug level. The validator name is prefixed automatically!"""
        self.reddit.log.debug(f'[{type(self).__name__}] ' + message)


class SubmissionValidator(Validator):
    def validate(self, submission: Submission) -> Tuple[Action, Rule]:
        return Action.PASS, Rule.NONE


class CommentValidator(Validator):
    def validate(self, comment: Comment) -> Tuple[Action, Rule]:
        return Action.PASS, Rule.NONE
