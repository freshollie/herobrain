import asyncio
import logging
import random
from datetime import datetime, timezone

from herobrain import networking
from aiohttp.client_exceptions import ContentTypeError, ClientConnectorError
from herobrain.game import GameHandler
from herobrain.output import HQHeroInterface


class Herobrain: 
    GAME_INFO_PATH = "/shows/now"

    def __init__(self, token, output_addr, quiz_api):
        self._log = logging.getLogger(Herobrain.__name__)
        self._log.info("Initialising")

        self._interface = HQHeroInterface(output_addr)

        self._info_api_url = f"{quiz_api}{Herobrain.GAME_INFO_PATH}"

        self._token = token
        self._headers = {"Authorization": f"Bearer {token}",
                         "x-hq-client": "Android/1.5.0"}
                         
        self._event_loop = asyncio.get_event_loop()

    async def _find_game(self):
        while True:
            try:
                response_data = await networking.get_json_response(self._info_api_url, timeout=1.5, headers=self._headers)
            except (ContentTypeError, asyncio.TimeoutError, ClientConnectorError) as e:
                self._log.error(f"_find_game: Could not get game info from server ({e}), retrying...")
                await asyncio.sleep(5)
                continue

            self._log.debug(response_data)

            if "broadcast" not in response_data or response_data["broadcast"] is None:
                if "error" in response_data and response_data["error"] == "Auth not valid":
                    raise RuntimeError("Invalid auth token")
                else:
                    # No show scheduled
                    if not response_data["nextShowTime"]:
                        next_time = None
                        prize = None
                        self._log.info("No show scheduled")
                    else:
                        next_time = datetime.strptime(response_data["nextShowTime"], "%Y-%m-%dT%H:%M:%S.000Z")
                        next_time = next_time.replace(tzinfo=timezone.utc)
                        prize = response_data["nextShowPrize"]

                        self._log.info(f"Next show at {next_time.isoformat()}")

                        # The game is a while away, so don't poll. Wait an hour and
                        # check again, or wake up close to game time
                        time_till_show = (next_time - datetime.utcnow().replace(tzinfo=timezone.utc)).total_seconds()
                        self._log.debug(f"{round(time_till_show)} seconds till next show")

                self._interface.report_waiting(next_time, prize)

                time_till_show = 0
                if next_time:
                    time_till_show = (next_time - datetime.utcnow().replace(tzinfo=timezone.utc)).total_seconds()
                
                if time_till_show > 60:
                    sleep_time = random.randint(60, 120)
                    self._log.debug("Sleeping")

                    while sleep_time > 0:
                        self._interface.report_waiting(next_time, prize)
                        sleep_time -= 5
                        await asyncio.sleep(5)
                else:
                    await asyncio.sleep(2)
            else:
                game_socket_addr = response_data["broadcast"]["socketUrl"].replace("https", "wss")
                self._log.info("Got a game socket %s" % game_socket_addr)
                return game_socket_addr
    
    async def _main_loop(self):
        while True:
            # Wait for the next game
            game_socket_addr = await self._find_game()
            
            self._interface.report_starting()
            # Play this game
            game = GameHandler(game_socket_addr, self._headers, self._interface)
            await game.play()

            await asyncio.sleep(5)
    
    def run(self):
        self._event_loop.run_until_complete(self._main_loop())
