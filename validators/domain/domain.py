from praw.models import Submission

from typing import Tuple

from reddit.enums import Rule, Action
from reddit.validator import SubmissionValidator


class DomainValidator(SubmissionValidator):
    __slots__ = ['domains']

    def __init__(self, reddit):
        super().__init__(reddit)
        self.domains = dict(reddit.config.items('domains'))

    def validate(self, submission: Submission) -> Tuple[Action, Rule]:
        if submission.is_self:
            return Action.PASS, Rule.NONE
        elif any(host in submission.url for host in self.domains['approved'].split(',')):
            return Action.APPROVE, Rule.NONE
        elif any(host in submission.url for host in self.domains['rejected'].split(',')):
            return Action.REMOVE, Rule.DOMAIN

        return Action.PASS, Rule.DOMAIN


def setup(reddit):
    reddit.add_extension(DomainValidator(reddit))
