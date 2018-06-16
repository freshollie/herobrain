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
    
    def report_prediction(self, question_num, answer_predictions):
        pass
    
    def report_round_end(self, answer_counts, correct_answer, eliminated, advancing):
        self._print_gap()
        print("Question over!")
        for answer in answer_counts:
            print(f'- {answer}({answer_counts[answer]}){" <- Correct" if answer == correct_answer else ""}')
        
        print()
        print(f"{eliminated} eliminated")
        print(f"{advancing} advancing")
        pass
    
    def report_finished(self):
        self._print_gap()
        print("Game has finished")