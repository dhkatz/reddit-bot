import errno
import os
from datetime import datetime

from peewee import *

try:
    os.makedirs(os.path.abspath(os.path.join(os.path.dirname(__file__), '../data')))
except OSError as e:
    if e.errno != errno.EEXIST:
        raise e


class Database:
    db = SqliteDatabase(os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/reddit.db')))

    __slots__ = []

    def __init__(self):
        self.db.create_tables([Submission, Comment, StickyComment, StickySubmission])

    @staticmethod
    def get_submission(id):
        return Submission.get_or_none(Submission.id == id)

    @staticmethod
    def get_comment(id):
        return Comment.get_or_none(Comment.id == id)

    @staticmethod
    def get_sticky_comment(id):
        return StickyComment.get_or_none(StickyComment.id == id)

    @staticmethod
    def create_submission(submission):
        return Submission.get_or_create(id=submission.id, subreddit=submission.subreddit, title=submission.title,
                                        flair=submission.flair, author=submission.author,
                                        is_epic=epic_author(submission))

    @staticmethod
    def create_comment(comment):
        return Comment.get_or_create(id=comment.id, submission=comment.submission.id, subreddit=comment.subreddit,
                                    author=comment.author, is_epic=epic_author(comment))

    @staticmethod
    def create_sticky_comment(comment):
        return StickyComment.get_or_create(id=comment.id, submission=comment.submission.id, subreddit=comment.subreddit,
                                            author=comment.author, is_epic=epic_author(comment))

    @staticmethod
    def count_epic(submission_id):
        return Comment.select().where(Comment.submission == submission_id & Comment.is_epic == True).count()


def epic_author(post) -> bool:
    return post.author_flair_css_class.lower() == 'epic'


class BaseModel(Model):
    class Meta:
        database = Database.db


class Submission(BaseModel):
    id = CharField(primary_key=True, unique=True)
    subreddit = CharField()
    title = CharField()
    flair = CharField(null=True)  # Might not have a flair
    author = CharField()
    is_epic = BooleanField(default=False)


class Comment(BaseModel):
    id = CharField(primary_key=True, unique=True)
    submission = CharField()
    subreddit = CharField()
    author = CharField()
    is_epic = BooleanField(default=False)


class StickyComment(Comment):
    created = DateTimeField(default=datetime.utcnow())


class StickySubmission(Submission):
    created = DateTimeField(default=datetime.utcnow())
