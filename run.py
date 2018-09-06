'''
MIT License

Copyright (c) 2018, Oliver Bell <freshollie@gmail.com> 
                  & Kevin Wu <github.com/Exaphis>
'''

import logging
import argparse
from herobrain import Herobrain
from herobrain import localisation
import sys


# Get the token as input
parser = argparse.ArgumentParser(description="Herobrain, a quiz prediction processor")
parser.add_argument("-t", "--token", dest="token", default="", help="HQTrivia bearer token")
parser.add_argument("-s", "--output", dest="output", default="http://localhost:1029", help="HQhero server")
parser.add_argument("-l", "--locale", 
                    dest="locale", 
                    default=localisation.ENGLISH_UK, 
                    choices=[localisation.ENGLISH_UK, 
                             localisation.ENGLISH_US, 
                             localisation.GERMANY],
                    help="Configures methods of question analysis")
parser.add_argument("--test", action="store_true", dest="test", help="Run in test mode, doesn't require bearer token")
parser.add_argument("--quiz-api", dest="quiz_api", default="https://api-quiz.hype.space", help="HQTrivia quiz-api")   
parser.add_argument("--test-api", dest="test_api", default="http://localhost:8732", help="Simulated quiz-api, requires --test")
parser.add_argument("--log-level", dest="log_level", default="info", choices=["critical", "error", "warning", "info", "debug"])

args = parser.parse_args()

if not args.test and not args.token:
    sys.exit("Token is required when not in test mode")

# Set the localisation
localisation.set_as(args.locale)

# Set up logging
logging.basicConfig(level=args.log_level.upper())
logging.getLogger('websockets').setLevel(logging.ERROR)

service = Herobrain(args.token, args.output, args.test_api if args.test else args.quiz_api)
service.run()
