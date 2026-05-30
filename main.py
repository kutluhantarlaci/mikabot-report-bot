"""
Quick one-off test: sends help + egitim to MikaBot and prints responses.
"""
import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()
API_ID = int(os.environ['TELEGRAM_API_ID'])
API_HASH = os.environ['TELEGRAM_API_HASH']
MIKABOT_USERNAME = 'tradermikabot'

client = TelegramClient('session', API_ID, API_HASH)
collected_responses = []


@client.on(events.NewMessage(from_users=MIKABOT_USERNAME))
async def on_mikabot_response(event):
    if event.text:
        print(f"\n[MikaBot] {event.text}\n")
        collected_responses.append(event.text)


async def send_command(command: str, wait: int = 6):
    print(f"[Sending] {command}")
    await client.send_message(MIKABOT_USERNAME, command)
    await asyncio.sleep(wait)


async def main():
    await client.start()
    print("Logged in.\n")

    await send_command('help')
    await send_command('egitim')

    if not collected_responses:
        print("No responses received from MikaBot.")

    await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
