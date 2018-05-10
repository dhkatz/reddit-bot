import configparser
import inspect
import os
import logging

from typing import Tuple

from praw.models import Submission, Comment

from .enums import Action, Rule


class Validator:
    """Represents a base :class:`Validator` to all other subclasses.

    This implements basic configuration, logging, and processing functinality.

    Attributes
    ----------
    reddit: praw.Reddit
        The main bot instance. Used to access configuration attributes
    config: configparser.ConfigParser
    """
    __slots__ = ['_praw', 'config', 'reddit']

    def __init__(self, reddit):
        super().__init__()
        self._praw = reddit.reddit
        self.reddit = reddit
        self.config = configparser.ConfigParser()
        # Magic to dynamically load a file relative to the current class executing
        if os.path.isfile(os.path.join(os.path.dirname(inspect.stack()[1][1]), 'config.ini')):
            self.config.read(os.path.join(os.path.dirname(inspect.stack()[1][1]), 'config.ini'))
        self.reddit.scheduler.register_job(type(self).__name__, 15, self.process, self.reddit.log)

    def process(self):
        """Base processing implementation. Gets called on an interval for validator processing."""
        pass

    def dlog(self, message: str):
        """Log messages at the debug level. The validator name is prefixed automatically!

        Parameters
        ----------
        message: str
            The message to log.
        """
        self.reddit.log.debug(f'[{type(self).__name__}] ' + message)

    def ilog(self, message: str):
        self.reddit.log.info(f'[{type(self).__name__}] ' + message)


class SubmissionValidator(Validator):
    """Base :class:`Validator` used for validators meant to validate a Submission"""
    def validate(self, submission: Submission) -> Tuple[Action, Rule]:
        """Validate a submission and return a verdict.

        Parameters
        ---------
        submission: praw.models.Submission
            Submission to be validated.

        Returns
        -------
        Action, Rule
            Action and Rule enums based on the validation computed.

        """
        return Action.PASS, Rule.NONE

    def dlog(self, message: str):
        """Log messages at the debug level. The validator name is prefixed automatically!

        Parameters
        ----------
        message: str
            The message to log.
        """
        if 'submission' in self.config.get('logging', 'type') or '*' in self.config.get('logging', 'type'):
            self.reddit.log.debug(f'[{type(self).__name__}] ' + message)


class CommentValidator(Validator):
    """Base Validator used for validators meant to validate a Submission"""
    def validate(self, comment: Comment) -> Tuple[Action, Rule]:
        """Validate a submission and return a verdict.

        Parameters
        ---------
        comment: praw.models.Submission
            Submission to be validated.

        Returns
        -------
        Action, Rule
            Action and Rule enums based on the validation computed.

        """
        return Action.PASS, Rule.NONE

    def dlog(self, message: str):
        """Log messages at the debug level. The validator name is prefixed automatically!

        Parameters
        ----------
        message: str
            The message to log.
        """
        if 'comment' in self.config.get('logging', 'type') or '*' in self.config.get('logging', 'type'):
            self.reddit.log.debug(f'[{type(self).__name__}] ' + message)
