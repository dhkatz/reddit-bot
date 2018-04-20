from praw.models import Submission

from reddit.enums import Valid, Rule
from reddit.validator import SubmissionValidator


class DomainValidator(SubmissionValidator):
    __slots__ = ['domains']

    def __init__(self, reddit):
        super().__init__(reddit)
        self.domains = dict(reddit.config.items('domains'))

    def validate(self, submission: Submission) -> Valid:
        if submission.is_self:
            return True, None
        elif any(host in submission.url for host in self.domains['approved'].split(',')):
            return True, None
        elif any(host in submission.url for host in self.domains['rejected'].split(',')):
            return False, Rule.DOMAIN

        return True, None


def setup(reddit):
    reddit.add_extension(DomainValidator(reddit))
