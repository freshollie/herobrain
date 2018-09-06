import aiohttp
import asyncio
import sys

HEADERS = {
    "x-hq-device": "iPhone9,3",
    "x-hq-client": "iOS/1.3.18 b106",
    "x-hq-timezone": "Europe/Lodnon",
    "x-hq-country": "gb",
    "x-hq-lang": "en",
    "x-hq-test-key": "",
    "User-Agent": "HQ-iOS/106 CFNetwork/902.2 Darwin17.7.0"
}

async def make_post(url, data):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.post(url, data=data) as response:
            return await response.json()


async def main():
    number = input("Number?: ")

    resp = await make_post("https://api-quiz.hype.space/verifications", {"phone": number, "method": "sms"})

    if "error" in resp:
        sys.exit(resp["error"])
    print(resp)
    verification_id = resp["verificationId"]

    code = input("Code?: ")

    resp = await make_post("https://api-quiz.hype.space/verifications/" + verification_id, {"code": code})

    if "error" in resp:
        sys.exit(resp["error"])
    print(resp)

    print(resp["auth"]["authToken"])

asyncio.get_event_loop().run_until_complete(main())
