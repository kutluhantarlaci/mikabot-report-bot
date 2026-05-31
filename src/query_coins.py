"""
One-off: runs deep-dive commands for NEAR, BANANAS31, ZEC + market checks.
"""
import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()
API_ID   = int(os.environ['TELEGRAM_API_ID'])
API_HASH = os.environ['TELEGRAM_API_HASH']
MIKABOT  = 'tradermikabot'

client  = TelegramClient('session', API_ID, API_HASH)
_buffer = []

@client.on(events.NewMessage(from_users=MIKABOT))
async def on_msg(event):
    if event.text:
        _buffer.append(event.text)


async def send(cmd: str, wait: int = 14) -> list:
    _buffer.clear()
    print(f'[{datetime.now().strftime("%H:%M:%S")}] → {cmd}')
    await client.send_message(MIKABOT, cmd)
    await asyncio.sleep(wait)
    result = list(_buffer)
    for r in result:
        print(r)
    print()
    return result


async def main():
    await client.start()
    print('Connected.\n')

    results = {}

    # Market-wide checks
    results['ssreport']      = await send('ssreport',      wait=16)
    results['weakcoin']      = await send('weakcoin',      wait=14)
    results['BestLongShort'] = await send('BestLongShort', wait=16)

    # Per-coin deep-dive: NEAR (buy candidate)
    results['sr near']  = await send('sr near')
    results['ls near']  = await send('ls near')
    results['t near']   = await send('t near')

    # Per-coin deep-dive: BANANAS31 (sell candidate)
    results['sr bananas31'] = await send('sr bananas31')
    results['ls bananas31'] = await send('ls bananas31')
    results['t bananas31']  = await send('t bananas31')

    # Per-coin deep-dive: ZEC (watch - weakening)
    results['sr zec'] = await send('sr zec')
    results['ls zec'] = await send('ls zec')
    results['t zec']  = await send('t zec')

    # Save raw results
    os.makedirs('data', exist_ok=True)
    with open('data/query_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('Saved to data/query_results.json')

    await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
