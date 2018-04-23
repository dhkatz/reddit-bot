# Fortnite - Reddit Bot

## Introduction

**Official Reddit Bot of both [/r/Fortnite](https://www.reddit.com/r/FORTnITE/) and [/r/FortniteBR](https://www.reddit.com/r/FortNiteBR/)**

Designed to make moderators not want to hate life when they open the moderator queue.

## Code Samples

### Validators

In order to easily adapt to new challenges, the bot uses a system of "validators" to validate every comment and post made on the subreddit.
Validators are essentially the "rules" of the subreddit. Posts that break these rules are removed automatically.

#### Insight Into Validators

Validators are, in short, classes with a `validate()` method derived from either the base `Validator` class or some subclass.

Validators that are intended to validate submissions must derive from the `SubmissionValidator` class (or some subclass of it), and validators intended to validate comments must derive from the `CommentValidator` class (or some subclass of it).

If you choose to subclass the base `Validator`, meaning not either `SubmissionValidator` or `CommentValidator` (or some subclass of them),
then your validator will be considered *generic* and validator *both* submissions and comments.

Here is a simple example of validator, called `DomainValidator`, designed to check submission urls against approved/banned URLs in the config:

```python
from typing import Tuple

from praw.models import Submission

from reddit.enums import Action, Reason
from reddit.validator import SubmissionValidator


class DomainValidator(SubmissionValidator):
    __slots__ = ['domains']

    def __init__(self, reddit):
        super().__init__(reddit)
        self.domains = dict(reddit.config.items('domains'))

    def validate(self, submission: Submission) -> Tuple[Action, Reason]:
        if submission.is_self:
            return Action.PASS, Rule.NONE
        elif any(host in submission.url for host in self.domains['approved'].split(',')):
            return Action.APPROVE, Rule.NONE
        elif any(host in submission.url for host in self.domains['rejected'].split(',')):
            return Action.REMOVE, Reason.DOMAIN

        return Action.PASS, Reason.NONE


def setup(reddit):
    reddit.add_extension(DomainValidator(reddit))
```

#### Creating a Validator

Creating a validator is simple. The best way to get started is by looking at the existing validators.

Validators must follow the following structure:

* Be placed inside a folder with the name of the validator (i.e validators/domain)
* Have a Python file inside the folder with the same name as the folder (i.e domain/domain.py)
* Contain a class based on either Validator/SubmissionValidator/CommentValidator (i.e class SomeValidator(Validator))
* Class name is suffixed with Validator (i.e Some**Validator**)
* Contain a setup function that takes a single argument (the Reddit instance)

See one of the included validators for more information.

#### Actions and Reasons

Something all validators must do is return two value (a tuple). These values
are the action to take on the submission/comment and the reason for said action.

Fortunately two enums are provided for you under the names `Action` and `Rule`.

**Action**

Actions are accessed by importing `Action` from `.reddit.enums`.

The current actions available in the `Action` enum are:

<br>

|  Action |                     Description                     |
|:-------:|:---------------------------------------------------:|
| REMOVE  | Set item to be removed immediately.                 |
| APPROVE | Set item to be approved immediately.                |
| MANUAL  | Set item to be skipped for manual (human) approval. |
| PASS    | Ignore item (pass to next validator).               |

All validators choosing to pass on an item is equivalent to one validator
choosing to force manual approval.

You can access these actions through dot notation access (i.e `Action.REMOVE`).

**Rule**

Rules are accessed by importing `Rule` from `.reddit.enums`.

The current rules available in the `Rule` enum are:

<br>

|    Rule   |                                          Description                                         |
|:---------:|:--------------------------------------------------------------------------------------------:|
| FLAIR     | [Flair guidelines.](https://www.reddit.com/r/FortNiteBR/wiki/rules)                          |
| DOMAIN    | Domain is banned from the subreddit.                                                         |
| PROMOTION | [Promotion rules.](https://www.reddit.com/r/FortNiteBR/wiki/rules#wiki_promotion_guidelines) |

You can access these rules through dot notation access (i.e `Rule.FLAIR`).

However, if you want the raw string for the rule (the actual text), you can convert the enum to a string by using the
`str` method (i.e `str(Rule.DOMAIN)`).

Currently, you *are* required to return both an `Action` and `Rule` for `CommentValidator`'s, but the rule is ignored.

## Installation

### Requirements

* Python 3.6+
* PRAW
* peewee
* apscheduler
* youtube_dl
* namedlist

### Install

1. Download or clone the repository contents
2. If desired, create a virtualenv for the repository
3. Launch a command terminal and enter `pip install -r requirements.txt`
4. Create a config.ini file either inside the reddit folder or somewhere else (copy the path if somewhere else)
5. Launch main.py using `python3 main.py path\to\config.ini` (If you placed config.ini inside reddit\ you do not have to do this)
