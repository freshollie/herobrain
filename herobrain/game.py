'''
MIT License

Copyright (c) 2018, Oliver Bell <freshollie@gmail.com> 
'''

import asyncio
import datetime
import json
import logging
import operator
import time
import re
import socket

import websockets
from unidecode import unidecode

from herobrain import networking
from herobrain.analysis import QuestionAnalyser


class GameHandler:
    MORE_LOGS = False

    def __init__(self, socket_addr, headers, interface):
        self._log = logging.getLogger(GameHandler.__name__)
        self._log.info("Initialising on %s" % socket_addr)

        self._socket_addr = socket_addr
        self._socket_headers = headers
    
        self._interface = interface
        self._event_loop = asyncio.get_event_loop()
    
    async def _on_new_round(self, question, choices, number, num_questions):
        start_time = time.time()
        self._interface.report_question(question, choices, number, num_questions)

        analyser = QuestionAnalyser(question, choices)
        self._interface.report_analysis(analyser.get_analysis(), number)

        # Find the probability of answers
        answers, analysis = await analyser.find_answers()
        speed = round(time.time() - start_time, 2)
        
        self._interface.report_prediction(number, answers, speed, analysis)
    
    async def _on_round_complete(self, answer_counts, correct_answer, eliminated, advancing):
        self._interface.report_round_end(answer_counts, correct_answer, eliminated, advancing)

    async def _handle_event(self, message):
        # New question
        if message["type"] == "question":
            # decode the question
            question_str = unidecode(message["question"])
            choices = [unidecode(ans["text"]) for ans in message["answers"]]

            question_num = message['questionNumber']
            num_questions = message['questionCount']

            await self._on_new_round(question_str, choices, question_num, num_questions)
        
        # Round is over
        elif message["type"] == "questionSummary":    
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

        elif message["type"] == "interaction":
            pass

    def _is_ending_message(self, message):
        return message["type"] == "broadcastEnded" and "reason" not in message
    
    async def _keep_open(self, socket):
        self._log.debug("Keeping socket open, pinging every 5 seconds")
        while True:
            try:
                await socket.ping()
            except (websockets.ConnectionClosed, KeyboardInterrupt):
                break
            await asyncio.sleep(5)
        self._log.debug("Ping loop ended")

    async def _game_connection(self):
        self._log.debug("Starting game connection")
        async with websockets.connect(self._socket_addr, extra_headers=self._socket_headers) as socket:
            asyncio.ensure_future(self._keep_open(socket))

            async for msg in socket:
                # We received a new message, remove any weird characters and
                message_data = json.loads(re.sub(r"[\x00-\x1f\x7f-\x9f]", "", msg))

                if GameHandler.MORE_LOGS:
                    self._log.debug(str(message_data))

                # Ah. Not good
                if "error" in message_data and message_data["error"] == "Auth not valid":
                    self._log.debug(message_data)
                    raise RuntimeError("Bad token")

                yield message_data

    async def play(self):
        try:
            while True:
                # Stay in this loop until
                # we get a connection closed error
                async for message in self._game_connection():
                    if self._is_ending_message(message):
                        self._log.info(f"Game ending: {message}")
                        return
                    # Don't stop receiving messages while we wait for the question to be answered
                    # perform the analysis in another coroutine
                    asyncio.ensure_future(self._handle_event(message))

        except (websockets.ConnectionClosed, ConnectionResetError):
            self._log.warning("%s closed unexpectedly" % self._socket_addr)
        except (ConnectionRefusedError, socket.gaierror) as e:
            self._log.error("Could not connect to %s: %s" % (self._socket_addr, e))
