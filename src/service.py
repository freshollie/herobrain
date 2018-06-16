import asyncio
import logging
import os
import time
from datetime import datetime
from reporting import HQwackInterface
import networking
from player import GameAnalyser

class HQwackBot: 
    GAME_INFO_URL = "https://api-quiz.hype.space/shows/now?type="

    def __init__(self, token, interface_addr):
        self._log = logging.getLogger(HQwackBot.__name__)
        self._log.info("Initialising")

        self._interface = HQwackInterface(interface_addr)

        self._token = token
        self._headers = {"Authorization": f"Bearer {token}",
                         "x-hq-client": "Android/1.3.0"}
                         
        self._event_loop = asyncio.get_event_loop()

    async def _find_game(self):
        try:
            response_data = await networking.get_json_response(HQwackBot.GAME_INFO_URL, timeout=1.5, headers=self._headers)
        except:
            self._log.error("_find_game: Server response not JSON, retrying...")
            return

        self._log.debug(response_data)

        if "broadcast" not in response_data or response_data["broadcast"] is None:
            if "error" in response_data and response_data["error"] == "Auth not valid":
                raise RuntimeError("Connection settings invalid")
            else:
                next_time = datetime.strptime(response_data["nextShowTime"], "%Y-%m-%dT%H:%M:%S.000Z")
                prize = response_data["nextShowPrize"]

                self._interface.report_waiting(next_time, prize)
        else:
            game_socket_addr = response_data["broadcast"]["socketUrl"].replace("https", "wss")
            return game_socket_addr
        
        return None
    
    async def _main_loop(self):
        while True:
            game_socket_addr = await self._find_game()
            
            if game_socket_addr:
                player = GameAnalyser(game_socket_addr, self._headers, self._interface)
                await player.play()
            else:
                time.sleep(5)
    
    def run(self):
        self._event_loop.run_until_complete(self._main_loop())
