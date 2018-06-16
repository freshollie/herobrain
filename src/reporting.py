import aiohttp
import logging
import asyncio

class HQwackInterface:
    def __init__(self, interface_addr):
        self._log = logging.getLogger(HQwackInterface.__name__)
        self._log.info("Initialising for %s" % interface_addr)

        self._addr = interface_addr
        self._event_loop = asyncio.get_event_loop()

    def _print_gap(self):
        print("========")
    
    def report_waiting(self, next_game_time, next_prize):
        self._print_gap()
        print("Waiting for next game")
        print("Next game: %s" % next_game_time.isoformat())
        print("Next prize: %s" % next_prize)
    
    def report_starting(self):
        self._print_gap()
        print("Game starting!")
    
    def report_question(self, question, answers, question_num, num_questions):
        self._print_gap()
        print("Question %s/%s" % (question_num, num_questions))
        print()
        print(question)
        print()
        for answer in answers:
            print("- %s" % answer)
        print()
    