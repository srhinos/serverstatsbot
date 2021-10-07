import os

from serverstatsbot import StatsBot, Settings

parser = Settings.get_cmdline_parser()
args = parser.parse_args()
args = {key: value for key, value in vars(args).items() if value is not None}

StatsBot(**args).run()
print("exiting")
os._exit(1)
