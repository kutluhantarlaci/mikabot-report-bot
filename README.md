# MikabotReportBot

A Python bot that connects to [MikaBot](https://t.me/tradermikabot) — a Turkish crypto signal Telegram bot — collects market data, and runs AI-powered analysis via Groq.

## Features

- **Discovery mode** — sends every MikaBot command once, saves all responses to `data/knowledge_base.json`
- **Test mode** — quick one-off check (`help` + `egitim` commands)
- **Monitor mode** — continuous market monitoring, runs at exact :00 :30 clock boundaries
- **AI analysis** — Groq (llama-3.3-70b) analyses MikaBot data every cycle and sends summary to Telegram Saved Messages
- **Deep-dive** — after monitor cycle, runs sr/ls/t for every buy+sell candidate, filters with hard rules before NLS alarms
- **Auto NLS alarms** — sets MikaBot exit alarms only for deep-dive-confirmed coins, auto-closes futures positions when 15m + 1h turn bearish
- **Sell scanner** — detects overbought coins for short positions (MTS ≥ 1.5, BLS ≤ 2, not weakcoin), sets auto-close alarms on MikaBot

## Requirements

- Python 3.10+
- A [Telegram API app](https://my.telegram.org/apps) (free)
- A [Groq API key](https://console.groq.com) (free tier available)
- A MikaBot subscription

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-username/MikabotReportBot.git
cd MikabotReportBot
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash
GROQ_API_KEY=your_groq_api_key
```

### 3. First run (Telegram login)

On first run, Telethon will ask for your phone number and a confirmation code sent by Telegram. This creates a `session.session` file — subsequent runs skip this step.

## Usage

Run everything through the launcher:

```bash
python src/runner.py
```

You will be prompted to choose a mode:

```
1 - discovery   run all MikaBot commands once, build knowledge base
2 - monitor     continuous market monitoring + AI coin suggestions
3 - main        quick one-off test (help + egitim)
```

While a mode is running, type `restart` to restart it or `stop` to quit.

**Or double-click a shortcut in `scripts/`:**

| File | Mode |
|---|---|
| `scripts/discovery.bat` | Discovery |
| `scripts/monitor.bat` | Monitor |
| `scripts/main.bat` | Main |

### Monitor mode output

Every 30 minutes the bot:
1. Fetches: `ka`, `ssreport`, `MarketAnaliz`, `ap`, `BestLongShort`, `strongcoin`, `weakcoin`, `ci s2 d`, `inout`, `dayhigh`
2. Runs Groq AI analysis on the combined data
3. Prints the analysis to the terminal
4. Sends it to your own Telegram "Saved Messages"

### Discovery mode output

Saves all MikaBot responses to `data/knowledge_base.json`.

## Project Structure

```
MikabotReportBot/
├── src/
│   ├── runner.py   # Mode launcher with restart/stop control
│   ├── monitor.py   # Continuous monitor + Groq AI analysis
│   ├── discovery.py   # One-time command discovery
│   ├── main.py   # Quick one-off test
│   ├── commands.py   # Command lists and monitor schedule
│   └── query_coins.py
├── utils/
│   ├── read_pdfs.py   # PDF reader utility
│   ├── generate_commands_pdf.py
│   └── update_readme.py   # Auto-updates this README before each commit
├── scripts/
│   ├── discovery.bat   # Double-click to start Discovery mode
│   ├── monitor.bat   # Double-click to start Monitor mode
│   └── main.bat   # Double-click to start Main mode
├── data/
│   ├── knowledge_base.json   # Discovery output
│   └── market_log.json       # Monitor log (last 500 entries)
├── assets/                   # MikaBot PDF guides
├── requirements.txt
├── .env   # Your secrets (not committed)
└── .env.example   # Template for .env
```

## Environment Variables

| Variable | Where to get it |
|---|---|
| `TELEGRAM_API_ID` | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `TELEGRAM_API_HASH` | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
