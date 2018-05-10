from typing import Tuple
from urllib.parse import urlparse, parse_qs

import isodate
import requests
from praw.models import Submission

from reddit.enums import Rule, Action
from reddit.validator import SubmissionValidator


class YoutubeValidator(SubmissionValidator):
    __slots__ = ['api']

    def __init__(self, reddit):
        super().__init__(reddit)
        self.api = 'https://www.googleapis.com/youtube/v3/videos?id={id}&key={key}&part=contentDetails'

    def validate(self, submission: Submission) -> Tuple[Action, Rule]:
        if any(url in submission.url for url in self.config.get('youtube', 'domains').split(',')):
            if 'channel' in submission.url or 'live' in submission.url:
                return Action.REMOVE, Rule.PROMOTION
            else:
                video_id = self.get_id(submission.url)
                response = requests.get(self.api.format(id=video_id, key=self.config.get('youtube', 'api')))
                if 300 > response.status_code >= 200:
                    data = response.json()
                else:
                    raise ConnectionError

                duration = isodate.parse_duration(data['items'][0]['contentDetails']['duration']).total_seconds()

                if duration > self.config.getfloat('general', 'time_limit'):
                    return Action.REMOVE, Rule.PROMOTION
                else:
                    return Action.APPROVE, Rule.NONE

        return Action.PASS, Rule.NONE

    @staticmethod
    def get_id(url):
        u_pars = urlparse(url)
        query_v = parse_qs(u_pars.query).get('v')
        if query_v:
            return query_v[0]
        pth = u_pars.path.split('/')
        if pth:
            return pth[-1]


class PushShift:
    API = 'https://api.pushshift.io/reddit'

    COMMENT_API = API + '/search/comment'
    SUBMISSION_API = API + '/search/submission'

    def comment_count(self, author: str, subreddit: str) -> int:
        """Get the number of comments made by a Redditor(s) on a subreddit(s).

        Parameters
        ----------
        author: str
            A single Redditor username or a comma separated list of usernames.
        subreddit: str
            A single subreddit or a comma separated list of subreddits.

        Returns
        -------
        int
            Total count of all comments for the given author(s) and subreddit(s).
            Returns -1 if request failed.
        """
        with requests.get(self.COMMENT_API + f'?author={author}&subreddit={subreddit}&aggs=subreddit&size=0') as r:
            if 300 > r.status_code >= 200:
                json = r.json()
            else:
                return -1

        return sum(subreddit['doc_count'] for subreddit in json['aggs']['subreddit'])


class PromotionValidator(SubmissionValidator):
    __slots__ = ['video', 'youtube', 'push_shift']

    def __init__(self, reddit):
        super().__init__(reddit)
        self.youtube = YoutubeValidator(reddit)
        self.push_shift = PushShift()

    def validate(self, submission: Submission) -> Tuple[Action, Rule]:
        if not any(url in submission.url for url in self.reddit.config.get('domains', 'watched').split(',')):
            return Action.PASS, Rule.NONE
        elif any(url in submission.url for url in self.reddit.config.get('domains', 'approved').split(',')):
            return Action.APPROVE, Rule.NONE
        elif any(url in submission.url for url in self.reddit.config.get('domains', 'rejected').split(',')):
            # We're checking domain rule because we don't want to depend on other validators
            return Action.REMOVE, Rule.DOMAIN

        self.dlog('Found watched URL in submission!')

        subs = ','.join([sub.split('-')[0] for sub in self.reddit.config.get('general', 'subreddits').split('+')])
        count = self.push_shift.comment_count(submission.author, subs)

        if count < self.config.getint('general', 'comment_limit'):
            if self.youtube.validate(submission)[0] == Action.REMOVE:
                self.ilog(f'Removing video longer than {self.config.getfloat("general", "time_limit")} seconds.')
                return Action.REMOVE, Rule.PROMOTION
            else:
                return Action.APPROVE, Rule.NONE
        else:
            return Action.MANUAL, Rule.NONE


def setup(reddit):
    reddit.add_extension(PromotionValidator(reddit))
