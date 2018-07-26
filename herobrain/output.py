import aiohttp
import logging
import asyncio
import operator
import time
import datetime

QUIET = False

class HQheroInterface:
    WAITING = "/hero/waiting"
    STARTING = "/hero/starting"
    NEWROUND = "/hero/round"
    ANALYSIS = "/hero/analysis"
    PREDICTION = "/hero/prediction"
    ANSWERS = "/hero/answers"
    FINISHED = "/hero/ended"
    
    def __init__(self, interface_addr):
        self._log = logging.getLogger(HQheroInterface.__name__)
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
                        self._log.error(f"Error response from hqhero for {url}: {data}")
            except (aiohttp.ClientError, aiohttp.client_exceptions.ClientConnectorError, ConnectionRefusedError) as e:
                self._log.error(f"Could not send info to {url}: {e}")
    
    def _send_info(self, endpoint, info={}):
        '''
        Send info is a wrapper around __do_send
        to push the send job onto the asyncio loop.

        This means that sending to hqhero does not block
        the brain from continueing to predict the next round
        '''

        asyncio.ensure_future(self.__do_send(endpoint, info))

    def _print(self, s=None):
        if not QUIET:
            print(s)

    def _print_gap(self):
        self._print("========")
    
    def report_waiting(self, next_game_time=None, next_prize=None):
        self._print_gap()

        if next_game_time:
            self._print("Waiting for next game")
            self._print("Next game: %s" % next_game_time.isoformat())
            self._print("Next prize: %s" % next_prize)
            self._send_info(HQheroInterface.WAITING, 
                            {"prize": next_prize, 
                            "nextGame": next_game_time.isoformat()})
        else:
            self._print("Next game not scheduled")
            self._send_info(HQheroInterface.WAITING, 
                            {"prize": None, 
                            "nextGame": None})
                            
    def report_starting(self):
        self._print_gap()
        self._print("Game starting!")
        self._score = 0
        self._round_num = 0
        self._predicted_answer = None

        self._send_info(HQheroInterface.STARTING)
    
    def report_question(self, question, answers, question_num, num_questions):
        self._print_gap()
        self._print("Question %s/%s" % (question_num, num_questions))
        self._print()
        self._print(question)
        self._print()
        for answer in answers:
            self._print("- %s" % answer)
        self._print()

        self._round_num = question_num

        self._send_info(HQheroInterface.NEWROUND, 
                        {"question": {"question": question, "choices": answers}, 
                         "numRounds": num_questions,
                         "num": question_num})
    
    def report_analysis(self, analysis, question_num):
        self._print("### Analysis ###")
        for key in analysis:
            self._print(f"- {key}: {analysis[key]}")
        
        self._send_info(HQheroInterface.ANALYSIS, {"analysis": analysis, "roundNum": question_num})

    def report_prediction(self, question_num, answer_predictions, speed, analysis):
        self._print()
        self._print("Prediction: ")

        self._predicted_answer = max(answer_predictions.items(), key=operator.itemgetter(1))[0]
        self._prediction_analysis = analysis

        for answer in answer_predictions:
            self._print(f" - {answer} - {round(answer_predictions[answer] * 100)}% {'<- Most probable' if answer == self._predicted_answer else ''}")
        self._print()
        self._print(f"Speed: {speed}s")

        self._send_info(HQheroInterface.PREDICTION, 
                        {"prediction": {"answers": answer_predictions, 
                                       "best": self._predicted_answer, 
                                       "speed": speed} , 
                         "roundNum": question_num})
        '''{'type': 'interaction', 'ts': '2018-06-19T14:11:02.525Z', 'itemId': 'chat', 'userId': 12762299, 'metadata': {'userId': 12762299, 'message': 'Morons', 'avatarUrl': 'https://d2xu1hdomh3nrx.cloudfront.net/72x72/a/98/12762299-GOroQ9.jpg', 'interaction': 'chat', 'username': 'Benjy613'}, 'sent': '2018-06-19T14:11:02.529Z'}'''
    
    def report_round_end(self, answer_counts, correct_answer, eliminated, advancing):
        self._print_gap()
        self._print("Round over!")

        for answer in answer_counts:
            self._print(f'- {answer}({answer_counts[answer]}){" <- Answer" if answer == correct_answer else ""}')

        # Analyse the accuracy of each method
        if self._prediction_analysis:
            for i in range(len(self._prediction_analysis)):
                analysis_answer = max(self._prediction_analysis[i].items(), key=operator.itemgetter(1))[0]
                self._analysis_correct_counts[i].append(1 if analysis_answer == correct_answer else 0)

        self._print()
        self._print("Accuracy per method: ")

        for i in range(len(self._analysis_correct_counts)):
            self._print(f"Method {i} - {0 if not self._analysis_correct_counts[i] else round((sum(self._analysis_correct_counts[i]) / len(self._analysis_correct_counts[i])) * 100, 2)}% ({len(self._analysis_correct_counts[i])})")
        
        self._print()
        self._print(f"{eliminated} eliminated")
        self._print(f"{advancing} advancing")

        if self._predicted_answer == correct_answer:
            self._score += 1
            self._correct_counts.append(1)
            self._print("Predicted correctly!")
        else:
            self._correct_counts.append(0)
        
        self._print(f"Prediction rate: {round((sum(self._correct_counts) / len(self._correct_counts)) * 100, 2)}%")

        self._print(f"Prediction score: {sum(self._correct_counts)}/{len(self._correct_counts)}")

        self._send_info(HQheroInterface.ANSWERS, 
                        {"conclusion": {"answers": answer_counts, 
                                        "answer": correct_answer, 
                                        "eliminated": eliminated,
                                        "advancing": advancing}})

    def report_finished(self):
        self._print_gap()
        self._print("Game has finished")
