from collections import deque
from typing import Tuple

from reddit.enums import Action, Rule
from reddit.validator import Validator


class AllValidator(Validator):
    def __init__(self, reddit):
        super().__init__(reddit)
        self._store = deque(maxlen=100)

    def process(self):
        for submission in self._praw.subbreddit('all').hot(limit=25):
            if submission is None:
                break

            if submission.subreddit.display_name.lower() in self.config.get('general', 'subreddits'):
                self._store.appendleft(submission.id)
                if submission.flair_css_class:
                    submission.mod.flair(text='r/all', css_class=submission.flair_css_class)
                else:
                    submission.mod.flair(text='r/all')

    def validate(self, post) -> Tuple[Action, Rule]:
        return Action.PASS, Rule.NONE
