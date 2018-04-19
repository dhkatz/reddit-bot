from typing import Optional

from praw.models import Comment, Submission

from reddit.enums import Valid
from reddit.validator import CommentValidator


class EpicValidator(CommentValidator):
    def __init__(self, reddit):
        super().__init__(reddit)

    def validate(self, comment: Comment) -> Valid:
        if comment.author_flair_css_class and comment.author_flair_css_class.lower() in self.config['general']['class']:
            sticky = self.has_sticky(comment.submission)
        else:
            return True, None

        if self.reddit.database.get_sticky_comment(comment.id):  # In case the bot some how has the Epic flair
            return True, None

        self.reddit.log.info('[Epic] Found comment by Epic ({0.author}): {0.body}'.format(comment))

        if sticky:
            if comment.id in sticky.body:  # It's already there somehow
                return True, None
            else:
                count = self.reddit.database.count_epic(comment.submission.id)
                sticky.edit(sticky.body + f'\n\n[Epic Comment {count + 1}](https://www.reddit.com{comment.permalink})')
                self.reddit.log.info(f'Updated stickied Epic comment tracker: https://www.reddit.com{sticky.permalink}')
        else:
            self.reddit.log.info('[Epic] Epic Comment post would have been created!')
            # reply = comment.submission.reply(f'Replies by Epic Games:\n\n'
            #                                  f'[Epic Comment 1](https://www.reddit.com{comment.permalink})')
            # reply.mod.distinguish(sticky=True)
            #
            # self._db.create_sticky_comment(reply)
            # self.log.info(f'Created new stickied Epic comment tracker: https://www.reddit.com{reply.permalink}')
        self.reddit.database.create_comment(comment)

    def has_sticky(self, submission: Submission) -> Optional[Comment]:
        for reply in submission.comments:
            if reply.stickied and self.reddit.database.get_sticky_comment(reply.id):
                return reply

        return None


def setup(reddit):
    reddit.add_extension(EpicValidator(reddit))
