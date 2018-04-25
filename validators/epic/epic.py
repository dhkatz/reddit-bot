from collections import deque, OrderedDict
from typing import Tuple, Optional

from praw.models import Comment, Submission

from reddit.enums import Action, Rule
from reddit.validator import CommentValidator

import namedlist


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


EpicComment = namedlist.namedtuple('EpicComment', [('id', ''), ('submission', '')])


class EpicValidator(CommentValidator):
    __slots__ = ['_sticky_store', '_comment_store']

    def __init__(self, reddit):
        super().__init__(reddit)
        self._sticky_store = LimitedSizeDict(size_limit=20)
        self._comment_store = deque(maxlen=200)

    def validate(self, comment: Comment) -> Tuple[Action, Rule]:
        css_class = comment.author_flair_css_class
        if not self.has_comment(comment) and css_class and css_class.lower() in self.config['general']['class']:
            self._comment_store.appendleft(EpicComment(comment.id, comment.submission.id))
        else:
            return Action.PASS, Rule.NONE  # Either we are already tracking or not a class we care about

        sticky = self.get_sticky(comment.submission)
        if sticky:
            sticky = self._praw.comment(id=sticky)
            if comment.permalink in sticky.body:  # We already posted the comment
                return Action.APPROVE, Rule.NONE

            sticky.edit(
                sticky.body + '\n\n[Epic Comment ' + str(self.num_epic_comments(comment.submission)) +
                f']({comment.permalink})'
            )
        else:
            sticky = comment.submission.reply(
                '##Comments by Epic Games:##\n\n' +
                f'[Epic Comment 1]({comment.permalink})'
            )
            sticky.mod.distinguish(sticky=True)
            self._sticky_store[comment.submission.id] = sticky.id

        return Action.APPROVE, Rule.NONE

    def get_sticky(self, submission: Submission) -> Optional[str]:
        if submission.id in self._sticky_store:
            return self._sticky_store[submission.id]
        else:  # In case the bot restarted let's check if it's already in the thread
            submission.comments.replace_more(limit=None)
            for comment in submission.comments.list():
                if comment.author.name == self._praw.user.me() and 'Comments by Epic Games' in comment.body:
                    self._sticky_store[submission.id] = comment.id
                    return comment.id
                else:
                    continue
        return None

    def has_comment(self, comment: Comment):
        return any(c.id == comment.id for c in self._comment_store)

    def num_epic_comments(self, submission: Submission) -> int:
        """Get the number of comments by Epic Games in a submission."""
        return sum(comment.submission == submission.id for comment in self._comment_store)


def setup(reddit):
    reddit.add_extension(EpicValidator(reddit))
