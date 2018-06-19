import aiohttp
import logging
import asyncio
import operator
import time
import datetime

class HQHeroInterface:
    WAITING = "/hero/waiting"
    STARTING = "/hero/starting"
    NEWROUND = "/hero/round"
    ANALYSIS = "/hero/analysis"
    PREDICTION = "/hero/prediction"
    ANSWERS = "/hero/answers"
    FINISHED = "/hero/ended"
    
    def __init__(self, interface_addr):
        self._log = logging.getLogger(HQHeroInterface.__name__)
        self._log.info("Initialising for %s" % interface_addr)

        self._addr = interface_addr
        self._score = 0
        self._num_rounds = 0
        self._predicted_answer = None
        self._event_loop = asyncio.get_event_loop()

        self._prediction_analysis = None
        self._question_time = 0
        self._event_loop = asyncio.get_event_loop()

        self._analysis_correct_counts = [[],[],[]]
        self._correct_counts = []

    async def __do_send(self, endpoint, info):
        url = self._addr + endpoint
        payload = { "info": info }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, timeout=20, json=payload) as response:
                    data = await response.json()
                    if "success" not in data:
                        self._log.error(f"Error response from hqwack for {url}: {data}")
            except (aiohttp.ClientError, aiohttp.client_exceptions.ClientConnectorError, ConnectionRefusedError) as e:
                self._log.error(f"Could not send info to {url}: {e}")
    
    def _send_info(self, endpoint, info={}):
        asyncio.ensure_future(self.__do_send(endpoint, info))

    def _print_gap(self):
        print("========")
    
    def report_waiting(self, next_game_time, next_prize):
        self._print_gap()
        print("Waiting for next game")
        print("Next game: %s" % next_game_time.isoformat())
        print("Next prize: %s" % next_prize)

        self._send_info(HQHeroInterface.WAITING, 
                        {"prize": next_prize, 
                         "nextGame": next_game_time.isoformat()})
    
    def report_starting(self):
        self._print_gap()
        print("Game starting!")
        self._score = 0
        self._round_num = 0
        self._predicted_answer = None

        self._send_info(HQHeroInterface.STARTING)
    
    def report_question(self, question, answers, question_num, num_questions):
        self._print_gap()
        print("Question %s/%s" % (question_num, num_questions))
        print()
        print(question)
        print()
        for answer in answers:
            print("- %s" % answer)
        print()

        self._round_num = question_num

        self._send_info(HQHeroInterface.NEWROUND, 
                        {"question": {"question": question, "choices": answers}, 
                         "numRounds": num_questions,
                         "num": question_num})
    
    def report_analysis(self, analysis, question_num):
        print("### Analysis ###")
        for key in analysis:
            print(f"- {key}: {analysis[key]}")
        
        self._send_info(HQHeroInterface.ANALYSIS, {"analysis": analysis, "roundNum": question_num})

    def report_prediction(self, question_num, answer_predictions, speed, analysis):
        print()
        print("Prediction: ")

        self._predicted_answer = max(answer_predictions.items(), key=operator.itemgetter(1))[0]
        self._prediction_analysis = analysis

        for answer in answer_predictions:
            print(f" - {answer} - {round(answer_predictions[answer] * 100)}% {'<- Most probable' if answer == self._predicted_answer else ''}")
        print()
        print(f"Speed: {speed}s")

        self._send_info(HQHeroInterface.PREDICTION, 
                        {"prediction": {"answers": answer_predictions, 
                                       "best": self._predicted_answer, 
                                       "speed": speed} , 
                         "roundNum": question_num})
        '''{'type': 'interaction', 'ts': '2018-06-19T14:11:02.525Z', 'itemId': 'chat', 'userId': 12762299, 'metadata': {'userId': 12762299, 'message': 'Morons', 'avatarUrl': 'https://d2xu1hdomh3nrx.cloudfront.net/72x72/a/98/12762299-GOroQ9.jpg', 'interaction': 'chat', 'username': 'Benjy613'}, 'sent': '2018-06-19T14:11:02.529Z'}'''
    
    def report_round_end(self, answer_counts, correct_answer, eliminated, advancing):
        self._print_gap()
        print("Round over!")

        for answer in answer_counts:
            print(f'- {answer}({answer_counts[answer]}){" <- Answer" if answer == correct_answer else ""}')

        # Analyse the accuracy of each method
        if self._prediction_analysis:
            for i in range(len(self._prediction_analysis)):
                analysis_answer = max(self._prediction_analysis[i].items(), key=operator.itemgetter(1))[0]
                self._analysis_correct_counts[i].append(1 if analysis_answer == correct_answer else 0)

        print()
        print("Accuracy per method: ")

        for i in range(len(self._analysis_correct_counts)):
            print(f"Method {i} - {0 if not self._analysis_correct_counts[i] else round((sum(self._analysis_correct_counts[i]) / len(self._analysis_correct_counts[i])) * 100, 2)}% ({len(self._analysis_correct_counts[i])})")
        
        print()
        print(f"{eliminated} eliminated")
        print(f"{advancing} advancing")

        if self._predicted_answer == correct_answer:
            self._score += 1
            self._correct_counts.append(1)
            print("Predicted correctly!")
        else:
            self._correct_counts.append(0)
        
        print(f"Prediction rate: {round((sum(self._correct_counts) / len(self._correct_counts)) * 100, 2)}%")

        print(f"Prediction score: {sum(self._correct_counts)}/{len(self._correct_counts)}")

        self._send_info(HQHeroInterface.ANSWERS, 
                        {"conclusion": {"answers": answer_counts, 
                                        "answer": correct_answer, 
                                        "eliminated": eliminated,
                                        "advancing": advancing}})

    def report_finished(self):
        self._print_gap()
        print("Game has finished")