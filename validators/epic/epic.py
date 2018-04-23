from collections import deque, OrderedDict
from typing import Tuple, Optional

from praw.models import Comment, Submission

from reddit.enums import Action, Rule
from reddit.validator import CommentValidator


class LimitedSizeDict(OrderedDict):
    def __init__(self, *args, **kwargs):
        self.size_limit = kwargs.pop("size_limit", None)
        OrderedDict.__init__(self, *args, **kwargs)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)


class EpicValidator(CommentValidator):
    __slots__ = ['_sticky_store', '_comment_store']

    def __init__(self, reddit):
        super().__init__(reddit)
        self._sticky_store = LimitedSizeDict(size_limit=20)
        self._comment_store = deque(maxlen=200)

    def validate(self, comment: Comment) -> Tuple[Action, Rule]:
        css_class = comment.author_flair_css_class
        if comment.id not in self._comment_store and css_class and css_class.lower() in self.config['general']['class']:
            self._comment_store.appendleft(comment.id)
        else:
            return Action.PASS, Rule.NONE  # Either we are already tracking or not a class we care about

        sticky = self.get_sticky(comment.submission)
        if sticky:
            sticky = self._praw.comment(id=sticky)
            sticky.edit(
                sticky.body + '\n\n[Epic Comment ' + str(len(self._sticky_store[sticky])) +
                f']({comment.shortlink})'
            )
        else:
            sticky = comment.submission.reply(
                '##Comments by Epic Games:##\n\n' +
                f'[Epic Comment 1]({comment.shortlink})'
            ).mod.distinguish(sticky=True)
            self._sticky_store[comment.submission.id] = sticky.id

    def get_sticky(self, submission: Submission) -> Optional[str]:
        if submission.id in self._sticky_store:
            return self._sticky_store[submission.id]

        return None


def setup(reddit):
    reddit.add_extension(EpicValidator(reddit))
