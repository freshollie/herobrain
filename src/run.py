import logging
import argparse
from service import HQHeroReporter

import colorama

# Set up color-coding
colorama.init()


# Get the token as input
parser = argparse.ArgumentParser(description="hqwack-reporter")
parser.add_argument("-t", "--token", dest="token", required=True)
parser.add_argument("-s", "--hqwack-interface", dest="interface", default="http://localhost:1029")
parser.add_argument("--test", action="store_true")
parser.add_argument("--test-game", dest="test_socket", default="ws://localhost:8765")
parser.add_argument("--log-level", dest="log_level", default="debug")

args = parser.parse_args()


# Set up logging
logging.basicConfig(level=args.log_level.upper())

service = HQHeroReporter(args.token, args.interface, args.test_socket if args.test else None)
service.run()
