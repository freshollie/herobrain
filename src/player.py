import networking
import logging
import re
import datetime
import json
from unidecode import unidecode
import analyser

class GameAnalyser:
    def __init__(self, socket_addr, headers, interface):
        self._log = logging.getLogger(GameAnalyser.__init__)
        self._log.init("Initialising on %s" % socket_addr)
        self._socket = networking.make_socket(socket_addr, headers)
    
        self._interface = interface

    async def _get_rounds(self):
        for msg in self._socket.connect(ping_rate=5):
            if msg.name != "text":
                continue

            # We received a new message
            # so parse it and hopefully get a JSON
            message = msg.text
            message = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", message)
            message_data = json.loads(message)
            self._log.debug(str(message_data).encode("utf-8"))

            # Ah. Not good
            if "error" in message_data and message_data["error"] == "Auth not valid":
                self._log.debug(message_data)
                raise RuntimeError("Bad token")

            # Something happened
            elif message_data["type"] != "interaction":
                self._log.debug(message_data)
                
                # New question
                if message_data["type"] == "question":
                    # decode the question
                    question_str = unidecode(message_data["question"])
                    answers = [unidecode(ans["text"]) for ans in message_data["answers"]]

                    question_num = message_data['questionNumber']
                    num_questions = message_data['questionCount']

                    yield question_str, answers, question_num, num_questions

    async def play(self):
        async for question, answers, question_num, num_questions in self._get_rounds():
            # Tell the interface we got a new question
            self._interface.report_question(question, answers, question_num, num_questions)

            # Find the probability of answers
            answers = await analyser.perform(question, answers)
                        
