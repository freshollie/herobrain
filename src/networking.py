import asyncio
import json
import logging
import re

import aiohttp
from colorama import Fore, Style
from lomond import WebSocket
from unidecode import unidecode

log = logging.getLogger(__name__)

async def fetch(url, session, timeout):
    try:
        async with session.get(url, timeout=timeout) as response:
            return await response.text()
    except Exception:
        print(f"Server timeout/error to {url}")
        logging.exception(f"Server timeout/error to {url}")
        return ""


async def get_responses(urls, timeout, headers):
    tasks = []
    async with aiohttp.ClientSession(headers=headers) as session:
        for url in urls:
            task = asyncio.ensure_future(fetch(url, session, timeout))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        return responses


async def get_response(url, timeout, headers):
    async with aiohttp.ClientSession(headers=headers) as session:
        return await fetch(url, session, timeout)


async def get_json_response(url, timeout, headers):
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, timeout=timeout) as response:
            return await response.json()


def make_socket(uri, headers):
    websocket = WebSocket(uri)
    for header, value in headers.items():
        websocket.add_header(str.encode(header), str.encode(value))
    return websocket
