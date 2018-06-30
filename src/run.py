import logging
import argparse
from service import HQHeroReporter
import localisation
import sys


# Get the token as input
parser = argparse.ArgumentParser(description="hqwack-reporter")
parser.add_argument("-t", "--token", dest="token", default="")
parser.add_argument("-s", "--server", dest="interface", default="http://localhost:1029")
parser.add_argument("-l", "--locale", dest="locale", default=localisation.ENGLISH_UK)
parser.add_argument("--test", action="store_true")
parser.add_argument("--test-game", dest="test_socket", default="ws://localhost:8765")
parser.add_argument("--log-level", dest="log_level", default="debug")

args = parser.parse_args()

if not args.test and not args.token:
    sys.exit("Token is required when not in test mode")

# Set the localisation
localisation.set_as(args.locale)

# Set up logging
logging.basicConfig(level=args.log_level.upper())
logging.getLogger('websockets').setLevel(logging.ERROR)

service = HQHeroReporter(args.token, args.interface, args.test_socket if args.test else None)
service.run()
