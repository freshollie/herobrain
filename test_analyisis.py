import asyncio
import logging
from herobrain.analysis import QuestionAnalyser
from herobrain import localisation
from herobrain import search

logging.basicConfig(level="DEBUG")
async def test_en():
    localisation.set_as(localisation.ENGLISH_UK)
    print(await QuestionAnalyser('What does the "P" in PSAT stand for?', 
                                    ["Practical", "Present", "Preliminary"]).find_answers())

async def test_de():
    localisation.set_as(localisation.GERMANY)
    print(await QuestionAnalyser("Wenn man \"Doppelkopf\" spielt, dann spielt man...?", ["Russisch Roulette falsh", "Ein Kartenspiel", "an sich rum"]).find_answers())

asyncio.get_event_loop().run_until_complete(search.search_google("test", 10))
