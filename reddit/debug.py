import logging, logging.config


class Debug:
    __slots__ = ['reddit']

    def __init__(self, reddit):
        self.reddit = reddit
