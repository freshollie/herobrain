import asyncio
import datetime
import json
import logging
import re

from unidecode import unidecode

import networking
from analysis import QuestionAnalyser
from reporting import HQwackInterface
import websockets

class HQTriviaPlayer:
    def __init__(self, socket_addr, headers, interface):
        self._log = logging.getLogger(HQTriviaPlayer.__name__)
        self._log.info("Initialising on %s" % socket_addr)

        self._socket_addr = socket_addr
        self._socket_headers = headers
    
        self._interface = interface
        self._event_loop = asyncio.get_event_loop()
    
    async def _play_round(self, question, answers, number, num_questions):
        self._interface.report_question(question, answers, number, num_questions)

        analyser = QuestionAnalyser(question, answers)
        print(analyser.get_analysis())

        # Find the probability of answers
        print(await analyser.find_answers())
    
    async def _on_round_complete(self, answer_counts, correct_answer, eliminated, advancing):
        self._interface.report_round_end(answer_counts, correct_answer, eliminated, advancing)

    async def _handle_event(self, message):
        self._log.debug(message)
        
        # New question
        if message["type"] == "question":
            # decode the question
            question_str = unidecode(message["question"])
            answers = [unidecode(ans["text"]) for ans in message["answers"]]

            question_num = message['questionNumber']
            num_questions = message['questionCount']

            await self._play_round(question_str, answers, question_num, num_questions)

        elif message["type"] == "questionSummary":
            # Round is over
            answer_counts ={}
            correct = ""
            for answer in message["answerCounts"]:
                ans_str = unidecode(answer["answer"])
                answer_counts[ans_str] = answer["count"]
                if answer["correct"]:
                    correct = ans_str

            advancing = message['advancingPlayersCount']
            eliminated = message['eliminatedPlayersCount']

            await self._on_round_complete(answer_counts, correct, eliminated, advancing)

    async def _game_connection(self):
        self._log.debug("Starting game connection")
        async with websockets.connect(self._socket_addr, extra_headers=self._socket_headers) as socket:
            async for msg in socket:
                self._log.debug("Recieved a message")

                # We received a new message
                # so parse it and hopefully get a JSON
                message = msg
                message = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", message)
                message_data = json.loads(message)
                self._log.debug(str(message_data).encode("utf-8"))

                # Ah. Not good
                if "error" in message_data and message_data["error"] == "Auth not valid":
                    self._log.debug(message_data)
                    raise RuntimeError("Bad token")
                
                if message_data["type"] != "interaction":
                    # Something happened
                    yield message_data

    async def play(self):
            try:
                while True:
                    # Stay in this loop until
                    # we get a connection closed error
                    async for message in self._game_connection():
                        asyncio.ensure_future(self._handle_event(message), loop=self._event_loop)
            except websockets.ConnectionClosed:
                self._log.warning("%s closed unexpectedly" % self._socket_addr)
            except ConnectionRefusedError as e:
                self._log.error("Could not connect to %s: %s" % (self._socket_addr, e))

if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    player = HQTriviaPlayer("ws://localhost:8765", {"lel": "kek"}, HQwackInterface("lel"))
    asyncio.get_event_loop().run_until_complete(player.play())
