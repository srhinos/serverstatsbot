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

        try:
            self.delay_first_fetch = timestamp_to_seconds(kwargs['delay_first_fetch'])
        except KeyError:
            self.delay_first_fetch = 0

        self.fetch_period = timestamp_to_seconds(kwargs.get('fetch_period', '1h'))

        try:
            self.delay_first_plot = timestamp_to_seconds(kwargs['delay_first_plot'])
        except KeyError:
            self.delay_first_plot = self.delay_first_fetch + 90

        self.plot_period = kwargs.get('plot_period', None)

        if self.plot_period:
            self.plot_period = timestamp_to_seconds(self.plot_period)

        self.check_validity()

    def check_validity(self):
        if not self.token:
            raise SettingsError('Token is not specified')

    @classmethod
    def get_cmdline_parser(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument("-T", "--token", help="specify token")
        parser.add_argument("-P", "--prefix", help="specify prefix")
        parser.add_argument(
            "-B", "--bot",
            help="specify whether token given is a bot (y/n), defaults to y. Note that using user token is risky"
        )

        parser.add_argument(
            "-df", "--delay-first-fetch",
            help="specify time to delay before bot does the first fetch"
        )
        parser.add_argument(
            "-fp", "--fetch-period",
            help="specify period for the bot to fetch the information"
        )
        parser.add_argument(
            "-dp", "--delay-first-plot",
            help="specify time to delay before bot does the first plot"
        )
        parser.add_argument(
            "-pp", "--plot-period",
            help="specify period for the bot to plot graphs. don't plot if not specified"
        )

        return parser
