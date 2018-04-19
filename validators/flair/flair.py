from collections import deque
from time import time

from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from praw.models import Submission

from reddit.scheduler import SmartScheduler
from reddit.enums import Reason, Valid
from reddit.validator import Validator


class FlairValidator(Validator):
    """Check if a post has flair."""
    __slots__ = ['_store', '_scheduler']

    def __init__(self, reddit):
        super().__init__(reddit)
        self._store = deque(maxlen=1000)
        executors = dict(default=ThreadPoolExecutor(20), processpool=ProcessPoolExecutor(5))
        job_defaults = dict(coalesce=True, max_instances=2)
        self._scheduler = SmartScheduler(BlockingScheduler(executors=executors, job_defaults=job_defaults))
        self._scheduler.register_job("Process", self.config.get('general', 'process_time'), self.process)

    def process(self):
        for submission in self._store:
            elapsed_time = time() - submission.created_utc
            if elapsed_time > self.config.get('general', 'warn_time') and submission.id not in self._store:
                author = self._praw.redditor(submission.author)
                author.message(
                    self.config.get('message', 'subject'),
                    self.config.get('message', 'body')
                        .format(post_url=submission.shortlink, time=self.config.get('general', 'remove_time'))
                )

            if elapsed_time > self.config.get('general', 'remove_time'):
                self._store.remove(submission.id)
                submission.reply(str(Reason.FLAIR)).mod.distinguish()
                submission.mod.remove()

    def validate(self, submission: Submission) -> Valid:
        if submission.link_flair_text is None:
            self._store.append(submission)
            return True, None  # We can't actually make a judgement yet


def setup(reddit):
    reddit.add_extension(FlairValidator(reddit))
