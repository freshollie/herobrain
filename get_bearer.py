import aiohttp
import asyncio
import sys

async def make_post(url, data):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as response:
            return await response.json()


async def main():
    number = input("Number?: ")

    resp = await make_post("https://api-quiz.hype.space/verifications", {"phone": number, "method": "sms"})

    if "error" in resp:
        sys.exit(resp["error"])

    verification_id = resp["verificationId"]

    code = input("Code?: ")

    resp = await make_post("https://api-quiz.hype.space/verifications/" + verification_id, {"code": code})

    if "error" in resp:
        sys.exit(resp["error"])

    print(resp["auth"]["authToken"])

asyncio.get_event_loop().run_until_complete(main())
