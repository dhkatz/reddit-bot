from collections import deque
from typing import Tuple

import praw.models

from reddit.enums import Action, Rule
from reddit.validator import SubmissionValidator


class AllValidator(SubmissionValidator):
    __slots__ = ['_store']

    def __init__(self, reddit):
        super().__init__(reddit)
        self._store = deque(maxlen=100)

    def process(self):
        for submission in self._praw.subreddit('all').hot(limit=25):
            if submission is None or (submission and submission.id in self._store):
                continue

            if submission.subreddit.display_name.lower() in self.reddit.config.get('general', 'subreddits'):
                self.dlog('Found post from {} in /r/all!'.format(submission.subreddit.display_name))
                self._store.appendleft(submission.id)
                if submission.flair_css_class:
                    submission.mod.flair(text='r/all', css_class=submission.flair_css_class)
                else:
                    submission.mod.flair(text='r/all')

    def validate(self, submission: praw.models.Submission) -> Tuple[Action, Rule]:
        return Action.PASS, Rule.NONE


def setup(reddit):
    reddit.add_extension(AllValidator(reddit))
