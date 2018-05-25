from praw.models import Submission

from reddit.enums import Rule, Action
from reddit.validator import SubmissionValidator


class TextValidator(SubmissionValidator):
    def validate(self, submission: Submission):
        if submission.is_self:
            return Action.APPROVE, Rule.NONE

        return Action.PASS, Rule.NONE


def setup(reddit):
    reddit.add_extension(TextValidator(reddit))
