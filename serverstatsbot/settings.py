import argparse

from .constants import prefix, token
from .utils import timestamp_to_seconds
from .exceptions import SettingsError


class Settings:
    def __init__(self, **kwargs):
        # @TheerapakG: I decided to put default here instead of parser in case that
        # we also load settings from json in the future
        self.token = kwargs.get('token', token)
        self.prefix = kwargs.get('prefix', prefix)
        self.bot = (kwargs.get('bot', 'y') == 'y')

        self.fetch_period = timestamp_to_seconds(kwargs.get('fetch_period', '1h'))
        self.check_validity()

    def check_validity(self):
        if not self.token:
            raise SettingsError('Token is not specified')

    @classmethod
    def get_cmdline_parser(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--token", help="specify token")
        parser.add_argument("-p", "--prefix", help="specify prefix")
        parser.add_argument(
            "-b", "--bot",
            help="specify whether token given is a bot (y/n), defaults to y. Note that using user token is risky"
        )

        parser.add_argument(
            "-fp", "--fetch-period",
            help="specify period for the bot to fetch the information"
        )

        return parser
