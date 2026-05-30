# MikabotReportBot

A Python bot that connects to [MikaBot](https://t.me/tradermikabot) — a Turkish crypto signal Telegram bot — collects market data, and runs AI-powered analysis via Groq.

## Features

- **Discovery mode** — sends every MikaBot command once and saves all responses to a local knowledge base
- **Monitor mode** — polls key market commands every 15 minutes, runs Groq AI analysis on the data, and sends a summary to your Telegram "Saved Messages"
- **Test mode** — quick one-off check (`help` + `egitim` commands)

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
python runner.py
```

You will be prompted to choose a mode:

```
1 - discovery   run all MikaBot commands once, build knowledge base
2 - monitor     continuous market monitoring + AI coin suggestions
3 - main        quick one-off test (help + egitim)
```

While a mode is running, type `restart` to restart it or `stop` to quit.

### Monitor mode output

Every 15 minutes the bot:
1. Fetches: `ka`, `ssreport`, `MarketAnaliz`, `ap`, `BestLongShort`, `strongcoin`, `weakcoin`, `ci s2 d`, `inout`, `dayhigh`
2. Runs Groq AI analysis on the combined data
3. Prints the analysis to the terminal
4. Sends it to your own Telegram "Saved Messages"

### Discovery mode output

Saves all MikaBot responses to `data/knowledge_base.json`.

## Project Structure

```
MikabotReportBot/
├── runner.py   # Mode launcher with restart/stop control
├── monitor.py   # Continuous monitor + Groq AI analysis
├── discovery.py   # One-time command discovery
├── main.py   # Quick one-off test
├── commands.py   # Command lists and monitor schedule
├── read_pdfs.py   # PDF reader utility
├── start-discovery.bat   # Double-click to start Discovery mode
├── start-monitor.bat   # Double-click to start Monitor mode
├── start-main.bat   # Double-click to start Main mode
├── requirements.txt
├── .env   # Your secrets (not committed)
├── .env.example   # Template for .env
├── update_readme.py   # Auto-updates this README before each commit
├── data/
│   ├── knowledge_base.json   # Discovery output
│   └── market_log.json       # Monitor log (last 500 entries)
└── assets/                   # MikaBot PDF guides
```

## Environment Variables

| Variable | Where to get it |
|---|---|
| `TELEGRAM_API_ID` | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `TELEGRAM_API_HASH` | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
