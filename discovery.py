"""
Run once to learn all MikaBot commands.
Saves responses to data/knowledge_base.json
"""
import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from commands import DISCOVERY_COMMANDS

load_dotenv()
API_ID = int(os.environ['TELEGRAM_API_ID'])
API_HASH = os.environ['TELEGRAM_API_HASH']
MIKABOT_USERNAME = 'tradermikabot'

client = TelegramClient('session', API_ID, API_HASH)
_buffer = []


@client.on(events.NewMessage(from_users=MIKABOT_USERNAME))
async def on_response(event):
    if event.text:
        _buffer.append(event.text)


async def send_and_collect(command: str, wait: int = 8) -> list:
    _buffer.clear()
    await client.send_message(MIKABOT_USERNAME, command)
    await asyncio.sleep(wait)
    return list(_buffer)


async def main():
    await client.start()
    print("Discovery started — this will take a few minutes...\n")

    os.makedirs('data', exist_ok=True)
    knowledge_base = {}

    for i, command in enumerate(DISCOVERY_COMMANDS, 1):
        print(f"[{i}/{len(DISCOVERY_COMMANDS)}] {command} ... ", end='', flush=True)
        responses = await send_and_collect(command)
        knowledge_base[command] = {
            'responses': responses,
            'timestamp': datetime.now().isoformat(),
        }
        print(f"{len(responses)} response(s)")
        await asyncio.sleep(4)

    with open('data/knowledge_base.json', 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Saved to data/knowledge_base.json")
    await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
