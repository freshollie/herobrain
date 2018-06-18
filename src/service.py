import asyncio
import logging
import os
import time
from aiohttp.client_exceptions import ContentTypeError
from datetime import datetime, timezone
from reporting import HQwackInterface
import networking
from player import HQTriviaPlayer

class HQwackReporter: 
    GAME_INFO_URL = "https://api-quiz.hype.space/shows/now?type="

    def __init__(self, token, interface_addr):
        self._log = logging.getLogger(HQwackReporter.__name__)
        self._log.info("Initialising")

        self._interface = HQwackInterface(interface_addr)

        self._token = token
        self._headers = {"Authorization": f"Bearer {token}",
                         "x-hq-client": "Android/1.3.0"}
                         
        self._event_loop = asyncio.get_event_loop()

    async def _find_game(self):
        while True:
            try:
                await asyncio.sleep(1)
                response_data={ "broadcast":{ "socketUrl": "ws://localhost:8765"} }
                #response_data = await networking.get_json_response(HQwackReporter.GAME_INFO_URL, timeout=1.5, headers=self._headers)
            except (ContentTypeError, TimeoutError):
                self._log.error("_find_game: Could not get game info from server, retrying...")
                await asyncio.sleep(5)
                continue

            self._log.debug(response_data)

            if "broadcast" not in response_data or response_data["broadcast"] is None:
                if "error" in response_data and response_data["error"] == "Auth not valid":
                    raise RuntimeError("Invalid auth token")
                else:
                    next_time = datetime.strptime(response_data["nextShowTime"], "%Y-%m-%dT%H:%M:%S.000Z")
                    next_time = next_time.replace(tzinfo=timezone.utc)
                    prize = response_data["nextShowPrize"]

                    self._interface.report_waiting(next_time, prize)
            else:
                game_socket_addr = response_data["broadcast"]["socketUrl"].replace("https", "wss")
                self._log.info("Got a game socket %s" % game_socket_addr)
                return game_socket_addr
            
            await asyncio.sleep(5)
    
    async def _main_loop(self):
        while True:
            # Wait for the next game
            game_socket_addr = await self._find_game()

            self._interface.report_starting()
            
            # Play this game
            player = HQTriviaPlayer(game_socket_addr, self._headers, self._interface)
            await player.play()
    
    def run(self):
        self._event_loop.run_until_complete(self._main_loop())
