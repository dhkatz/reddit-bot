import configparser


class Validator:
    __slots__ = ['_praw', 'config', 'reddit']

    def __init__(self, reddit):
        self._praw = reddit.reddit
        self.reddit = reddit
        self.config = configparser.ConfigParser()
        self.config.read('validators/' + str(type(self).__name__).lower().replace('validator', '') + '/config.ini')
