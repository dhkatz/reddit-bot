import json
import mimetypes
import shlex
import subprocess

import youtube_dl
from praw.models import Submission

from reddit.enums import Reason, Valid, Extension
from reddit.validator import Validator


class VideoValidator(Validator):
    __slots__ = ['extensions', 'ydl_opts']

    def __init__(self, reddit, quiet: bool = True):
        super().__init__(reddit)
        mimetypes.init()
        self.extensions = self.get_extensions()
        self.ydl_opts = {'quiet': quiet}

    @staticmethod
    def get_extensions() -> tuple:
        extensions = []
        for ext in mimetypes.types_map:
            if mimetypes.types_map[ext].split('/')[0] == 'video':
                extensions.append(ext)
        return tuple(extensions)

    @staticmethod
    def get_metadata(input_video):
        cmd = "ffprobe -v quiet -print_format json -show_streams"
        args = shlex.split(cmd)
        args.append(input_video)
        ffprobe_output = subprocess.check_output(args).decode('utf-8')
        ffprobe_output = json.loads(ffprobe_output)

        return ffprobe_output

    def find_url(self, data: dict):
        for k, v in data.items():
            if isinstance(v, str):
                if v.endswith(self.extensions):
                    return v
            elif isinstance(v, list):
                d = {}
                for i in range(len(v)):
                    d[str(i)] = v[i]
                return self.find_url(d)
            elif isinstance(v, dict):
                return self.find_url(v)

    def validate(self, submission: Submission) -> Valid:
        url = submission.url
        meta = None
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            try:
                meta = ydl.extract_info(url, download=False)
            except Exception as e:
                print(e)

        if meta is not None:
            if 'duration' in meta and meta['duration'] <= self.config.get('general', 'time_limit'):
                return True, None
            else:
                url = self.find_url(meta)
                try:
                    metadata = self.get_metadata(url)
                except Exception as e:
                    # print('ERROR', meta, e)
                    pass
                else:
                    print(metadata)
        return False, Reason.PROMOTION


class PromotionValidator(Validator):
    __slots__ = ['video_validator']

    def __init__(self, reddit):
        super().__init__(reddit)
        self.video_validator = VideoValidator(reddit)

    def validate(self, submission: Submission) -> Valid:
        if submission.url not in self.config.get('domains', 'watched').split(','):
            return True, None

        counter = 0
        for comment in submission.author.comments.new(limit=None):
            if comment.subreddit.display_name.lower() in self.reddit.SUBREDDITS:
                counter += 1
                if counter >= self.config.get('general', 'comment_limit'):
                    break

        if counter >= self.config.get('general', 'comment_limit') and self.video_validator.validate(submission):
            return True, None

        return False, Reason.PROMOTION


def setup(reddit):
    reddit.add_extension(Extension.SUBMISSION, PromotionValidator(reddit))