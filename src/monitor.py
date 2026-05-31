"""
Continuous market monitor with Groq AI analysis.
"""
# README: **Monitor mode** — continuous market monitoring, runs at exact :00 :15 :30 :45 clock boundaries
# README: **AI analysis** — Groq (llama-3.3-70b) analyses MikaBot data every cycle and sends summary to Telegram Saved Messages
# README: **Auto NLS alarms** — sets MikaBot exit alarms for every buy candidate, auto-closes futures positions when 15m + 1h turn bearish
import asyncio
import json
import os
import re
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from commands import MONITOR_SCHEDULE

load_dotenv()
API_ID = int(os.environ['TELEGRAM_API_ID'])
API_HASH = os.environ['TELEGRAM_API_HASH']
MIKABOT_USERNAME = 'tradermikabot'
GROQ_API_KEY = os.environ['GROQ_API_KEY']
GROQ_MODEL = 'llama-3.3-70b-versatile'
groq_client = Groq(api_key=GROQ_API_KEY)

client = TelegramClient('session', API_ID, API_HASH)
_buffer = []
_last_run: dict = {}
_market_snapshot: dict = {}
_last_analysis: datetime = None
_nls_alarms_sent: set = set()   # Tracks coins with active NLS alarms this session

# Coins that should never get a futures alarm
STABLECOINS = {'USDC', 'USDT', 'BUSD', 'DAI', 'TUSD', 'FDUSD', 'USDE'}

# NLS pattern for closing a long:
# --xxx = sellers dominant in 15m and 1h → exit signal
# (PDF recommends shorter timeframes for futures)
NLS_EXIT_PATTERN = '--xxx'

SYSTEM_PROMPT = """You are a crypto trading assistant analyzing data from MikaBot, a Turkish crypto signal bot.

=== METRIC DEFINITIONS ===
- SmartScore: Multi-parameter smart score. Only consider coins with SmartScore > 5 for trading.
- MTS (MinorTrendScore): Short-term price expensiveness. <1.0 = cheap, 1.0-1.5 = fair, >1.5 = expensive/overbought. If MTS is 1.7, wait for it to drop to 1.3-1.5 before buying.
- TS (TrendScore): Long-term price expensiveness. <0.5 = very cheap long-term.
- PT (PumpTrust): Pump reliability. >1.0 = reliable pump history. Do not buy if PT is much below 1.0.
- BestLongShort (0-5): Buy dominance across 5 timeframes (15m,1h,4h,12h,1d). 5=+++++ all buying, 0=----- all selling.
- Acc (Accumulation): >5 = strong panic buying. < -5 = strong panic selling. Positive is bullish.
- TrendString: Trend strength left=recent. +++++ = strong uptrend. ----- = strong downtrend.
- VLast_V24H: Last period volume / 24h average. >2 = volume surge.
- VolumePerc: Coin's share of total market volume. >3% = significant, reliable for trading.
- Buy Power (X): Market-wide buying strength. <0.5X = weak, >2X = strong.
- IncScore (CI report): >1.05 = strong buy correlation with BTC rise.

=== OFFICIAL MIKABOT STRATEGIES ===
Strategy 1 - SSR FILTER: ONLY trade coins appearing in the SSR (ssreport) list. Big rallies only come from SSR coins.

Strategy 2 - KURNAZ AVCI:
- Allocate 10-20% of portfolio per ka recommendation.
- PT must not be much below 1.0.
- If MTS > 1.7, wait for it to fall to 1.3-1.5 first.

Strategy 3 - AP (Altcoin Power) thresholds:
- Short-term AP > 95 → TAKE PROFITS (whales selling)
- Short-term AP < 5 → BUY altcoins (oversold, if no bad news)
- Long-term AP > 95 → Stay away from market for a few days
- Long-term AP < 5 (bear market) → Long-term investment opportunity
- Long-term AP: 5→20 = recovery, active trading begins

=== BUY CRITERIA (all should be met) ===
1. Coin is in SSR report (SmartScore > 5)
2. MTS below 1.5 (not overpriced)
3. BestLongShort >= 4 (buy dominant in most timeframes)
4. VolumePerc > 1% (has volume)
5. Positive Acc or hitting day high
6. Not in weakcoin list

=== AVOID / SELL SIGNALS ===
- In weakcoin list
- MTS > 1.5 (overpriced)
- BestLongShort 0-1 (sellers dominating)
- Strong negative Acc (< -5)
- AP short-term > 95 (take profits)

Always respond in English. Be specific — list coin names, their key metrics, and exact action."""


# ── Telegram event handler ──────────────────────────────────────────────────

@client.on(events.NewMessage(from_users=MIKABOT_USERNAME))
async def on_response(event):
    if event.text:
        _buffer.append(event.text)


# ── Persistence ─────────────────────────────────────────────────────────────

def _save_log(command: str, responses: list):
    os.makedirs('data', exist_ok=True)
    path = 'data/market_log.json'
    log = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                log = json.load(f)
            except Exception:
                pass
    log.append({
        'command': command,
        'timestamp': datetime.now().isoformat(),
        'responses': responses,
    })
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(log[-500:], f, ensure_ascii=False, indent=2)


# ── Display ──────────────────────────────────────────────────────────────────

def _display(command: str, responses: list):
    ts = datetime.now().strftime('%H:%M')
    print(f"\n{'='*60}")
    print(f"  [{ts}]  {command}")
    print('='*60)
    for r in responses:
        print(r)
    print('='*60)


# ── Data parsers ─────────────────────────────────────────────────────────────

def _fl(s: str) -> float:
    """Turkish-format float (comma decimal) → Python float."""
    try:
        return float(str(s).replace(',', '.'))
    except Exception:
        return 0.0


def _lines(command: str) -> list:
    """Flatten all response messages for a command into individual lines."""
    result = []
    for msg in _market_snapshot.get(command, []):
        result.extend(msg.splitlines())
    return result


def _parse_ssreport() -> dict:
    """Returns {SYMBOL: {ss, ts, mts, trend}} for all SSR coins."""
    result = {}
    for line in _lines('ssreport'):
        m = re.match(
            r'^(\w+USDT)\s+[\d,]+\s+'
            r'([+\-])\s+([+\-])\s+([+\-])\s+([+\-])\s+([+\-])\s+'
            r'\*\*([\d,]+)\*\*\s+([\d,NULL]+)\s+([\d,]+)',
            line
        )
        if m:
            symbol = m.group(1).replace('USDT', '')
            trend = m.group(2) + m.group(3) + m.group(4) + m.group(5) + m.group(6)
            ss = _fl(m.group(7))
            ts_raw = m.group(8)
            ts = _fl(ts_raw) if ts_raw != 'NULL' else None
            mts = _fl(m.group(9))
            result[symbol] = {'ss': ss, 'ts': ts, 'mts': mts, 'trend': trend}
    return result


def _parse_bestlongshort() -> dict:
    """Returns {SYMBOL: {score, pattern, vol}} from BestLongShort report."""
    result = {}
    for line in _lines('BestLongShort'):
        m = re.match(r'^(\w+USDT)=>(\d)\s+([+\-]{5})\s+V:%([\d,]+)', line)
        if m:
            symbol = m.group(1).replace('USDT', '')
            result[symbol] = {
                'score': int(m.group(2)),
                'pattern': m.group(3),
                'vol': _fl(m.group(4)),
            }
    return result


def _parse_weakcoin() -> set:
    """Returns set of weak coin symbols to avoid."""
    result = set()
    for line in _lines('weakcoin'):
        m = re.match(r'^([A-Z0-9]+)USDT\s+', line)
        if m:
            result.add(m.group(1))
    return result


def _parse_dayhigh() -> dict:
    """Returns {SYMBOL: {vlast, acc, mts}} for coins hitting 24h high."""
    result = {}
    for line in _lines('dayhigh'):
        m = re.match(
            r'^([A-Z0-9]+)USDT\s+[\d,]+\s+([-\d,]+)\s+([-\d,]+)\s+\*\*([\d,]+)\*\*',
            line
        )
        if m:
            symbol = m.group(1)
            result[symbol] = {
                'vlast': _fl(m.group(2)),
                'acc':   _fl(m.group(3)),
                'mts':   _fl(m.group(4)),
            }
    return result


def _parse_ap() -> dict:
    """Returns {short_btc, short, long} AP values."""
    result = {'short_btc': None, 'short': None, 'long': None}
    for line in _lines('ap'):
        m = re.search(r"Kısa Vadede Btc'ye.*?:\s*([\d,]+)", line)
        if m:
            result['short_btc'] = _fl(m.group(1))
        m = re.search(r"Kısa Vadede Gücü.*?:\s*([\d,]+)", line)
        if m:
            result['short'] = _fl(m.group(1))
        m = re.search(r"Uzun Vadede.*?:\s*([\d,]+)", line)
        if m:
            result['long'] = _fl(m.group(1))
    return result


def _parse_buy_power() -> float | None:
    """Returns market buy power multiplier (e.g. 0.7 from '0,7X')."""
    for line in _lines('inout'):
        m = re.search(r'Alım Gücü[^`]*`([\d,]+)X`', line)
        if m:
            return _fl(m.group(1))
    return None


# ── AI analysis ──────────────────────────────────────────────────────────────

def _build_context() -> str:
    """Pre-parse all MikaBot data into clean English for the AI."""
    ssr = _parse_ssreport()
    bls = _parse_bestlongshort()
    weak = _parse_weakcoin()
    dayhigh = _parse_dayhigh()
    ap = _parse_ap()
    buy_power = _parse_buy_power()

    lines = []

    lines.append("=== MARKET CONDITIONS ===")
    ap_long  = ap.get('long')
    ap_short = ap.get('short')
    ap_sbtc  = ap.get('short_btc')
    if ap_long is not None:
        if ap_long < 5:
            zone = "DEEP BEAR — long-term invest opportunity"
        elif ap_long < 20:
            zone = "RECOVERING — cautious buying ok, active trading begins"
        elif ap_long > 95:
            zone = "OVERBOUGHT — stay away"
        else:
            zone = "NEUTRAL"
        lines.append(f"AP Long-term: {ap_long}  → {zone}")
    if ap_short is not None:
        short_note = "OVERSOLD (buy signal)" if ap_short < 5 else ("OVERBOUGHT (take profits)" if ap_short > 95 else "neutral")
        lines.append(f"AP Short-term: {ap_short}  → {short_note}")
    if ap_sbtc is not None:
        lines.append(f"AP vs BTC (altcoin strength): {ap_sbtc}")
    if buy_power is not None:
        bp_note = "WEAK" if buy_power < 0.8 else ("STRONG" if buy_power > 1.5 else "moderate")
        lines.append(f"Market Buy Power: {buy_power}X  → {bp_note}")

    ma_lines = [l for l in _lines('MarketAnaliz') if l.strip()][:3]
    if ma_lines:
        lines.append("MarketAnaliz note: " + " | ".join(ma_lines))

    lines.append("")
    lines.append("=== KURNAZ AVCI RECOMMENDATIONS ===")
    ka_coins = []
    for line in _lines('ka'):
        m = re.match(r'^(\w+)\s+TS:([\d,]+)\s+MTS:([\d,]+)\s+PT:([\d,]+)', line)
        if m:
            ka_coins.append(
                f"{m.group(1)}: TS={_fl(m.group(2))}, MTS={_fl(m.group(3))}, PT={_fl(m.group(4))}"
                + (" ← PT>1.0 reliable" if _fl(m.group(4)) >= 1.0 else " ← PT<1.0 caution")
            )
    if ka_coins:
        lines.extend(ka_coins)
    else:
        lines.append("No Kurnaz Avcı recommendations right now (market appetite low).")

    lines.append("")
    lines.append("=== SSR COINS (SmartScore > 5) — these are the ONLY tradeable coins ===")
    lines.append("Format: COIN  SS=SmartScore  MTS=price_expensiveness  TS=longterm_value  BLS=buy_pressure/5  Vol%=market_volume")
    ssr_tradeable = [(s, d) for s, d in ssr.items() if d['ss'] >= 5]
    ssr_tradeable.sort(key=lambda x: -x[1]['ss'])
    for sym, d in ssr_tradeable:
        ls = bls.get(sym, {})
        ls_score = ls.get('score', '?')
        vol = ls.get('vol', 0.0)
        in_dh = sym in dayhigh
        is_weak = sym in weak
        flags = []
        if d['mts'] > 1.5:
            flags.append(f"⚠ MTS={d['mts']} OVERPRICED — do not buy")
        if is_weak:
            flags.append("⚠ weakcoin — avoid")
        if in_dh:
            acc = dayhigh[sym]['acc']
            flags.append(f"hitting 24h HIGH (Acc={acc})")
        flag_str = "  |  " + ", ".join(flags) if flags else ""
        ts_str = str(d['ts']) if d['ts'] is not None else "N/A"
        lines.append(
            f"  {sym:<8}  SS={d['ss']:<8.2f}  MTS={d['mts']:<5}  TS={ts_str:<5}"
            f"  BLS={ls_score}/5  Vol={vol:.1f}%{flag_str}"
        )

    lines.append("")
    lines.append("=== COINS HITTING 24H HIGH (momentum) ===")
    if dayhigh:
        for sym, d in dayhigh.items():
            in_ssr = sym in ssr
            ss_str = f"SS={ssr[sym]['ss']:.1f}" if in_ssr else "not in SSR"
            lines.append(
                f"  {sym:<8}  Acc={d['acc']:<6}  MTS={d['mts']}  VolumeX={d['vlast']}  {ss_str}"
            )
    else:
        lines.append("  None.")

    lines.append("")
    lines.append("=== WEAKCOIN LIST (avoid all of these) ===")
    lines.append("  " + ", ".join(sorted(weak)[:15]))

    return '\n'.join(lines)


def analyze_market() -> str:
    if not _market_snapshot:
        return "No data yet."

    context = _build_context()

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': (
                    f"MikaBot market data at {datetime.now().strftime('%H:%M')}:\n\n"
                    f"{context}\n\n"
                    "Using ONLY the data above (do not invent numbers), answer:\n\n"
                    "MARKET: Is it Safe / Neutral / Risky? One sentence citing AP long-term value and buy power.\n\n"
                    "BUY: Up to 5 coins. Only list coins that are IN THE SSR LIST with SmartScore>5 AND MTS<1.5 AND not weakcoin, OR are in Kurnaz Avcı. "
                    "For each: name, exact SmartScore from the data above, exact MTS, BLS score, reason.\n\n"
                    "AVOID: Coins to avoid and exact reason (overpriced MTS / weakcoin / low BLS).\n\n"
                    "ACTION: One concrete sentence on what to do right now.\n\n"
                    "Use ONLY numbers from the data above. Do not guess or estimate."
                )}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[Groq error: {e}]"


def print_analysis(analysis: str):
    print(f"\n{'*'*62}")
    print(f"  AI ANALYSIS  [{datetime.now().strftime('%H:%M')}]")
    print('*'*62)
    print(analysis)
    print('*'*62 + '\n')


async def notify_self(analysis: str):
    ts = datetime.now().strftime('%H:%M')
    text = f"📊 *MikaBot Analysis [{ts}]*\n\n{analysis}"
    try:
        await client.send_message('me', text, parse_mode='md')
    except Exception as e:
        print(f"[notify] Failed to send self-message: {e}")


# ── Command runner ───────────────────────────────────────────────────────────

async def run_command(command: str, wait: int = 10):
    _buffer.clear()
    print(f"[{datetime.now().strftime('%H:%M')}] Fetching: {command}")
    await client.send_message(MIKABOT_USERNAME, command)
    await asyncio.sleep(wait)
    responses = list(_buffer)
    if responses:
        _save_log(command, responses)
        _display(command, responses)
        _market_snapshot[command] = responses
        _last_run[command] = datetime.now()
    else:
        print(f"  [!] No response for '{command}' — will retry next cycle")


# ── NLS exit alarm setup ─────────────────────────────────────────────────────

def _get_buy_candidates() -> list:
    """Returns coins meeting strict buy criteria for NLS alarm setup."""
    ssr  = _parse_ssreport()
    bls  = _parse_bestlongshort()
    weak = _parse_weakcoin()

    candidates = []
    for sym, d in ssr.items():
        if sym in STABLECOINS:
            continue
        if sym in weak:
            continue
        if d['ss'] < 5:
            continue
        if d['mts'] >= 1.5:
            continue
        if bls.get(sym, {}).get('score', 0) < 4:
            continue
        candidates.append(sym)

    return candidates


async def setup_nls_alarms():
    """Send NLS exit alarm commands to MikaBot for all current buy candidates."""
    candidates = _get_buy_candidates()
    new_alarms = [c for c in candidates if c not in _nls_alarms_sent]

    if not new_alarms:
        print('[NLS] No new buy candidates — no alarms to set.')
        return

    for coin in new_alarms:
        cmd = f'Nls {coin} {NLS_EXIT_PATTERN}:order futures %100 {coin}'
        print(f'[NLS] Setting exit alarm: {cmd}')
        await client.send_message(MIKABOT_USERNAME, cmd)
        _nls_alarms_sent.add(coin)
        await asyncio.sleep(2)

    lines = [f'• {c}  →  `Nls {c} {NLS_EXIT_PATTERN}:order futures %100 {c}`' for c in new_alarms]
    msg = (
        f'🔔 *NLS Exit Alarms Set [{datetime.now().strftime("%H:%M")}]*\n\n'
        + '\n'.join(lines)
        + '\n\n_Auto-closes 100% of futures position when 15m + 1h turn bearish_'
    )
    await client.send_message('me', msg, parse_mode='md')
    print(f'[NLS] {len(new_alarms)} alarm(s) set: {", ".join(new_alarms)}')


# ── Clock alignment ──────────────────────────────────────────────────────────

def seconds_until_next_15min() -> float:
    """Returns seconds until the next :00, :15, :30, or :45 boundary."""
    now = datetime.now()
    total_seconds = now.minute * 60 + now.second + now.microsecond / 1_000_000
    elapsed_in_interval = total_seconds % 900  # 900s = 15 min
    if elapsed_in_interval == 0:
        return 0.0
    return 900 - elapsed_in_interval


# ── Main loop ────────────────────────────────────────────────────────────────

async def monitoring_loop():
    print("Market monitor running. Press Ctrl+C to stop.\n")
    print("Schedule: runs at every :00, :15, :30, :45\n")

    wait = seconds_until_next_15min()
    if wait > 0:
        next_run = (datetime.now() + timedelta(seconds=wait)).strftime('%H:%M')
        print(f"First run at {next_run} — waiting {int(wait // 60)}m {int(wait % 60)}s...\n")
        await asyncio.sleep(wait)

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M')}] Starting cycle...\n")

        for command in MONITOR_SCHEDULE:
            await run_command(command)
            await asyncio.sleep(5)

        print("[AI] Running analysis...")
        analysis = analyze_market()
        print_analysis(analysis)
        await notify_self(analysis)
        await setup_nls_alarms()

        wait = seconds_until_next_15min()
        if wait > 0:
            next_run = (datetime.now() + timedelta(seconds=wait)).strftime('%H:%M')
            print(f"Next cycle at {next_run} — waiting {int(wait // 60)}m {int(wait % 60)}s...\n")
            await asyncio.sleep(wait)


async def main():
    await client.start()
    print("Logged in.\n")
    await monitoring_loop()


if __name__ == '__main__':
    asyncio.run(main())
