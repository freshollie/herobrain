import logging
import argparse
from service import HQwackReporter

import colorama

# Set up color-coding
colorama.init()

# Set up logging
logging.basicConfig(level="DEBUG")

# Get the token as input
parser = argparse.ArgumentParser(description="hqwack-reporter")
parser.add_argument("-t", "--token", dest="token", required=True)
parser.add_argument("-s", "--hqwack-interface", dest="interface", default="http://localhost:1029")

args = parser.parse_args()

service = HQwackReporter(args.token, args.interface)
service.run()
