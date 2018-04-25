from collections import deque
from time import time
from namedlist import namedlist
from typing import Tuple

from praw.models import Submission

from reddit.enums import Rule, Action
from reddit.validator import SubmissionValidator

WatchedSubmission = namedlist('WatchedSubmission', [('id', ''), ('created', 0.0), ('warned', False)])


class FlairValidator(SubmissionValidator):
    """Check if a post has flair."""
    __slots__ = ['_store']

    def __init__(self, reddit):
        super().__init__(reddit)
        self._store = deque(maxlen=1000)

    def process(self):
        self._store = deque([submission for submission in list(self._store) if self.check(submission)])

    def check(self, watched_submission: WatchedSubmission) -> bool:
        elapsed_time = time() - watched_submission.created
        if elapsed_time < self.config.getint('general', 'warn_time'):
            return True  # We can avoid unnecessary requests by checking first!

        submission = self._praw.submission(watched_submission.id)

        if not watched_submission.warned and submission.link_flair_text is None:
            self.dlog('Warning user about an unflaired post!')
            author = submission.author
            author.message(
                self.config.get('message', 'subject'),
                self.config.get('message', 'body')
                    .format(post_url=submission.shortlink, time=int(self.config.getint('general', 'remove_time') / 60))
            )
            watched_submission.warned = True
            return True
        elif elapsed_time >= self.config.getint('general', 'remove_time') and submission.link_flair_text is None:
            self.dlog('Removing an unflaired post!')
            submission.reply(str(Rule.FLAIR)).mod.distinguish()
            submission.mod.remove()
            return False
        elif submission.link_flair_text is not None:
            return False

        return True

    def validate(self, submission: Submission) -> Tuple[Action, Rule]:
        if submission.link_flair_text is None:
            watch = WatchedSubmission(submission.id, submission.created_utc, False)
            self._store.appendleft(watch)
            self.dlog('Storing submission for later processing...')
            return Action.PASS, Rule.NONE  # We can't actually make a judgement yet


def setup(reddit):
    reddit.add_extension(FlairValidator(reddit))
