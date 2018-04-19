import configparser

from praw.models import Submission, Comment

from .enums import Valid

class Validator:
    __slots__ = ['_praw', 'config', 'reddit']

    def __init__(self, reddit):
        self._praw = reddit.reddit
        self.reddit = reddit
        self.config = configparser.ConfigParser()
        self.config.read('validators/' + str(type(self).__name__).lower().replace('validator', '') + '/config.ini')


class SubmissionValidator(Validator):
    def validate(self, submission: Submission) -> Valid:
        return True, None


class CommentValidator(Validator):
    def validate(self, comment: Comment) -> Valid:
        return True, None
