# Fortnite - Reddit Bot

## Introduction

**Official Reddit Bot of both [/r/Fortnite](https://www.reddit.com/r/FORTnITE/) and [/r/FortniteBR](https://www.reddit.com/r/FortNiteBR/)**

Designed to make moderators not want to hate life when they open the moderator queue.

## Code Samples

In order to easily adapt to new challenges, the bot uses a system of "validators" to validate every comment and post made on the subreddit.

Validators are, in short, classes with a `validate` method derived from either the base `Validator` class or some subclass. Validators that are intended to validate submissions must derive from the `SubmissionValidator` class (or some subclass of it), and validators intended to validate comments must derive from the `CommentValidator` class (or some subclass of it).

Here is a simple example of validator, called `DomainValidator`, designed to check submission urls against approved/banned URLs in the config:

```python
from praw.models import Submission

from reddit.enums import Valid, Reason
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
            return False, Reason.DOMAIN

        return True, None


def setup(reddit):
    reddit.add_extension(DomainValidator(reddit))
```

## Installation

Coming soon!