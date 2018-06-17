import aiohttp
import logging
import asyncio
import operator
import time

class HQwackInterface:
    def __init__(self, interface_addr):
        self._log = logging.getLogger(HQwackInterface.__name__)
        self._log.info("Initialising for %s" % interface_addr)

        self._addr = interface_addr
        self._score = 0
        self._num_rounds = 0
        self._predicted_answer = None
        self._question_time = 0
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
        self._score = 0
        self._round_num = 0
        self._predicted_answer = None
    
    def report_question(self, question, answers, question_num, num_questions):
        self._print_gap()
        print("Question %s/%s" % (question_num, num_questions))
        print()
        print(question)
        print()
        for answer in answers:
            print("- %s" % answer)
        print()

        self._question_time = time.time()
        self._round_num = question_num
    
    def report_analysis(self, analysis):
        print("### Analysis ###")
        for key in analysis:
            print(f"- {key}: {analysis[key]}")

    def report_prediction(self, question_num, answer_predictions):
        speed = round(time.time() - self._question_time, 2)
        print()
        print("Prediction: ")
        self._predicted_answer = max(answer_predictions.items(), key=operator.itemgetter(1))[0]

        for answer in answer_predictions:
            print(f" - {answer} - {round(answer_predictions[answer] * 100)}% {'<- Most probable' if answer == self._predicted_answer else ''}")
        print()
        print(f"Speed: {speed}s")
    
    def report_round_end(self, answer_counts, correct_answer, eliminated, advancing):
        self._print_gap()
        print("Round over!")
        for answer in answer_counts:
            print(f'- {answer}({answer_counts[answer]}){" <- Answer" if answer == correct_answer else ""}')
        
        print()
        print(f"{eliminated} eliminated")
        print(f"{advancing} advancing")

        if self._predicted_answer == correct_answer:
            self._score += 1
            print("Predicted correctly!")

        print(f"Prediction score: {self._score}/{self._round_num}")
    
    def report_finished(self):
        self._print_gap()
        print("Game has finished")