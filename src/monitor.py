"""
Continuous market monitor with Groq AI analysis.
"""
# README: **Monitor mode** — continuous market monitoring, runs at exact :00 :30 clock boundaries
# README: **AI analysis** — Groq (llama-3.3-70b) analyses MikaBot data every cycle and sends summary to Telegram Saved Messages
# README: **Deep-dive** — after monitor cycle, runs sr/ls/t for every buy+sell candidate, filters with hard rules before NLS alarms
# README: **Auto NLS alarms** — sets MikaBot exit alarms only for deep-dive-confirmed coins, auto-closes futures positions when 15m + 1h turn bearish
# README: **Sell scanner** — detects overbought coins for short positions (MTS ≥ 1.5, BLS ≤ 2, not weakcoin), sets auto-close alarms on MikaBot
import asyncio
import json
import os
import re
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from commands import MONITOR_SCHEDULE, MONITOR_INTERVAL

load_dotenv()
API_ID = int(os.environ['TELEGRAM_API_ID'])
API_HASH = os.environ['TELEGRAM_API_HASH']
MIKABOT_USERNAME = 'tradermikabot'
GROQ_API_KEY = os.environ['GROQ_API_KEY']
GROQ_MODEL = 'llama-3.3-70b-versatile'
groq_client = Groq(api_key=GROQ_API_KEY)

client = TelegramClient('session', API_ID, API_HASH)
_buffer = []
_market_snapshot: dict = {}
_nls_alarms_sent: set = set()         # Tracks coins with active long NLS alarms this session
_nls_short_alarms_sent: set = set()   # Tracks coins with active short NLS alarms this session
_deepdive_results: dict = {}          # {coin: {sr, ls, t, passed, rejects, warnings, mode}}

# Coins that should never get a futures alarm
STABLECOINS = {'USDC', 'USDT', 'BUSD', 'DAI', 'TUSD', 'FDUSD', 'USDE'}

# NLS pattern for closing a long: sellers in 15m + 1h → exit
NLS_LONG_EXIT_PATTERN  = '--xxx'
# NLS pattern for closing a short: buyers in 15m + 1h → exit
NLS_SHORT_EXIT_PATTERN = '++xxx'

SYSTEM_PROMPT = """You are a crypto trading assistant analyzing data from MikaBot, a Turkish crypto signal bot.

=== METRIC DEFINITIONS ===
- SmartScore: Multi-parameter smart score. Only consider coins with SmartScore > 5 for trading.
- MTS (MinorTrendScore): Short-term price expensiveness. Lower = cheaper, higher = more expensive/overbought. >1.5 = overpriced, do not buy. If MTS is 1.7, wait for it to drop to 1.3-1.5 before buying.
- TS (TrendScore): Long-term trend divergence indicator. >1.0 = upward long-term divergence. <1.0 = downward divergence. Used alongside MTS to confirm trend direction.
- PT (PumpTrust): Pump reliability. >1.0 = reliable pump history. Do not buy if PT is much below 1.0.
- BestLongShort (0-5): Buy dominance across 5 timeframes (15m,1h,4h,12h,1d). 5=+++++ all buying, 0=----- all selling. Pattern order: [15m][1h][4h][12h][1d].
- Price Acceleration (Acc): Price momentum. >5 = panic buying. < -5 = panic selling. Positive is bullish.
- TrendString: Trend strength, left=most recent. +++++ = strong uptrend. ----- = strong downtrend.
- Vol% (BestLongShort volume column): Coin's share of total market volume. >3% = significant and reliable for trading. >1% = minimum acceptable for entry.
- Buy Power (X): Market-wide buying strength. <0.8X = weak market. >1.5X = strong market.
- IncScore (CI report): Correlation with BTC rise intensity. >1.05 = strong buy when BTC rises.
- VLast_V24H: Volume last period / 24h average. >1 = above average. 2-3 = strong surge.
- VLast_VHigh: Volume last period / 10-day peak volume. >0.3 = good explosion. >0.5 = very strong.
- SVI: Smart Volatility Index. Low = squeezing/consolidating (potential breakout). High = volatile.
- HPriceInDay: True = coin reached today's 24h high in last 1.5h (correction risk).
- TrendLevels: Short-term support(-)/resistance(+) zones. (0) = price at this zone now. Leftmost = strongest.
- TrendLevels_Big: Medium-term support/resistance zones.

=== OFFICIAL MIKABOT STRATEGIES ===
Strategy 1 - SSR FILTER: ONLY trade coins appearing in the SSR (ssreport) list with SmartScore > 5. Big rallies only come from SSR coins.

Strategy 2 - KURNAZ AVCI:
- Allocate 10-20% of portfolio per ka recommendation.
- PT must not be much below 1.0.
- If MTS > 1.7, wait for it to fall to 1.3-1.5 first.

Strategy 3 - AP (Altcoin Power) thresholds:
- Short-term AP > 95 → TAKE PROFITS immediately (whales selling)
- Short-term AP < 5 → BUY altcoins (oversold, if no bad news)
- Long-term AP > 95 → Stay away from market for a few days
- Long-term AP < 5 (bear market) → Long-term investment opportunity
- Long-term AP crossing 5→20 = recovery phase, active trading begins

=== BUY CRITERIA (mirrors Kurnaz Avcı logic — all must be met) ===
1. Coin is in SSR report (SmartScore > 5)
2. MTS below 1.5 (not overpriced short-term)
3. BestLongShort = 5 (buyers dominant in ALL 5 timeframes +++++)
4. PT >= 1.0 if available from Kurnaz Avcı (reliable pump history)
5. TS < 1.0 if available (long-term undervalued). NULL TS is acceptable.
6. Not in weakcoin list

=== SELL/SHORT CRITERIA (both must be met) ===
1. Coin is in SSR report
2. MTS >= 1.5 (overpriced)
3. BestLongShort <= 2 (sellers dominant in 3 or more timeframes)
4. BLS pattern does NOT start with ++ (short-term buyers not already dominant)

=== AVOID (do not trade in any direction) ===
- In weakcoin list
- AP short-term > 95 (entire market overbought — take profits on everything)
- Strong negative Price Acceleration (< -5) with no SSR backing

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


def _parse_ka() -> dict:
    """Returns {SYMBOL: {ts, mts, pt}} from Kurnaz Avcı response."""
    result = {}
    for line in _lines('ka'):
        m = re.match(r'^(\w+)\s+TS:([\d,NULL]+)\s+MTS:([\d,]+)\s+PT:([\d,]+)', line)
        if m:
            ts_raw = m.group(2)
            result[m.group(1)] = {
                'ts':  _fl(ts_raw) if ts_raw != 'NULL' else None,
                'mts': _fl(m.group(3)),
                'pt':  _fl(m.group(4)),
            }
    return result


def _parse_buy_power() -> float | None:
    """Returns market buy power multiplier (e.g. 0.7 from '0,7X')."""
    for line in _lines('inout'):
        m = re.search(r'Alım Gücü[^`]*`([\d,]+)X`', line)
        if m:
            return _fl(m.group(1))
    return None


# ── Deep-dive command runner ─────────────────────────────────────────────────

async def _run_coin_command(command: str, wait: int = 12) -> list:
    """Send a per-coin command and return responses. Does NOT update _market_snapshot."""
    _buffer.clear()
    print(f"  [{datetime.now().strftime('%H:%M:%S')}] → {command}")
    await client.send_message(MIKABOT_USERNAME, command)
    await asyncio.sleep(wait)
    return list(_buffer)


# ── Deep-dive parsers ─────────────────────────────────────────────────────────

def _parse_sr(responses: list) -> dict:
    """Parse sr {coin} response into structured dict."""
    d = {
        'trend_string': None, 'acc': None, 'mts': None, 'ss': None,
        'vlast_v24h': None, 'vlast_vhigh': None, 'volume_perc': None,
        'svi': None, 'ch1h': None, 'ch24h': None,
        'hprice_in_day': None, 'trend_levels': '', 'trend_levels_big': '',
        'correlation_btc': None, 'raw': responses,
    }
    text = '\n'.join(responses)

    m = re.search(r'[Tt]rendstring[:\s]+([+\- ]+)', text)
    if m:
        d['trend_string'] = m.group(1).replace(' ', '')

    for field, pattern in [
        ('acc',           r'Acc[:\s]+([-\d,]+)'),
        ('mts',           r'MinorTrendScore[:\s]+([\d,]+)'),
        ('ss',            r'\bSs[:\s]+([\d,]+)'),
        ('vlast_v24h',    r'VLast_V24H[:\s]+([\d,]+)'),
        ('vlast_vhigh',   r'VLast_VHigh[:\s]+([\d,]+)'),
        ('svi',           r'\bSVI[:\s]+([\d,]+)'),
        ('ch1h',          r'Ch1h[:\s]*%?([-\d,]+)'),
        ('ch24h',         r'Ch24h[:\s]*%?([-\d,]+)'),
        ('correlation_btc', r'Correlation_BTC[:\s]+([-\d,]+)'),
    ]:
        m = re.search(pattern, text)
        if m:
            d[field] = _fl(m.group(1))

    m = re.search(r'VolumePerc[:\s]*%?([\d,]+)', text)
    if m:
        d['volume_perc'] = _fl(m.group(1))

    m = re.search(r'HPriceInDay[:\s]*(True|False)', text, re.IGNORECASE)
    if m:
        d['hprice_in_day'] = m.group(1).lower() == 'true'

    m = re.search(r'TrendLevels[:\s]+([^\n]+)', text)
    if m:
        d['trend_levels'] = m.group(1).strip()

    m = re.search(r'TrendLevels_Big[:\s]+([^\n]+)', text)
    if m:
        d['trend_levels_big'] = m.group(1).strip()

    return d


def _parse_ls(responses: list) -> dict:
    """Parse ls {coin} response — extract Long% per timeframe."""
    d = {'15m': None, '1h': None, '4h': None, '12h': None, '1d': None, 'raw': responses}
    text = '\n'.join(responses)
    for tf in ['15m', '1h', '4h', '12h', '1d']:
        m = re.search(rf'{tf}.*?Long[:\s]*%?([\d,]+)', text)
        if m:
            d[tf] = _fl(m.group(1))
    return d


def _parse_t(responses: list) -> dict:
    """Parse t {coin} response — extract support/resistance zones and at-zone flag."""
    d = {
        'at_zone': False,
        'short_destek': [], 'short_direnc': [],
        'orta_destek':  [], 'orta_direnc':  [],
        'raw': responses,
    }
    text = '\n'.join(responses)

    if 'Özel Not' in text or 'trend seviyesinde' in text.lower():
        d['at_zone'] = True

    kisa = re.search(r'Kısa vadede[;:\s]*(.*?)(?:Orta vadede|$)', text, re.DOTALL)
    if kisa:
        kisa_txt = kisa.group(1)
        m = re.search(r'Direnç[:\s]*([0-9,\.\s\-]+)', kisa_txt)
        if m:
            d['short_direnc'] = m.group(1).strip().split()
        m = re.search(r'Destek[:\s]*([0-9,\.\s\-]+)', kisa_txt)
        if m:
            d['short_destek'] = m.group(1).strip().split()

    orta = re.search(r'Orta vadede[;:\s]*(.*?)$', text, re.DOTALL)
    if orta:
        orta_txt = orta.group(1)
        m = re.search(r'Direnç[:\s]*([0-9,\.\s\-]+)', orta_txt)
        if m:
            d['orta_direnc'] = m.group(1).strip().split()
        m = re.search(r'Destek[:\s]*([0-9,\.\s\-]+)', orta_txt)
        if m:
            d['orta_destek'] = m.group(1).strip().split()

    return d


# ── Deep-dive filter logic ────────────────────────────────────────────────────

def _score_buy(coin: str, sr: dict, ls: dict, t: dict) -> tuple[bool, list, list]:
    """Returns (passed, hard_rejects, soft_warnings) for a buy candidate."""
    rejects, warnings = [], []

    # TrendString: hard reject on confirmed downtrend
    ts = (sr.get('trend_string') or '').replace(' ', '')
    if ts == '-----':
        rejects.append(f'TrendString=----- (strong downtrend)')
    elif ts.startswith('--'):
        warnings.append(f'TrendString={ts} (recent bearish)')

    # Acc: panic selling = reject
    acc = sr.get('acc')
    if acc is not None:
        if acc < -5:
            rejects.append(f'Acc={acc} (panic selling)')
        elif acc < 0:
            warnings.append(f'Acc={acc} (negative momentum)')

    # MTS: overpriced = reject
    mts = sr.get('mts')
    if mts is not None and mts >= 1.5:
        rejects.append(f'MTS={mts} (overpriced ≥1.5)')

    # Volume: very low = reject
    vl = sr.get('vlast_v24h')
    if vl is not None:
        if vl < 0.5:
            rejects.append(f'VLast_V24H={vl} (very low volume <0.5x)')
        elif vl < 1.0:
            warnings.append(f'VLast_V24H={vl} (below-average volume)')

    # HPriceInDay: at daily high = correction risk
    if sr.get('hprice_in_day') is True:
        warnings.append('HPriceInDay=True (at 24h high, correction risk)')

    # LS: spot buyers must be dominant in 15m and 1h
    l15 = ls.get('15m')
    l1h = ls.get('1h')
    l4h = ls.get('4h')
    if l15 is not None:
        if l15 < 50:
            rejects.append(f'15m Long={l15}% (spot sellers dominant)')
        elif l15 < 55:
            warnings.append(f'15m Long={l15}% (weak, <55%)')
    if l1h is not None:
        if l1h < 50:
            rejects.append(f'1h Long={l1h}% (spot sellers dominant)')
        elif l1h < 55:
            warnings.append(f'1h Long={l1h}% (weak, <55%)')
    if l4h is not None and l4h < 50:
        warnings.append(f'4h Long={l4h}% (medium-term selling)')

    # T: at zone and resistance nearby
    if t.get('at_zone'):
        warnings.append('Price at trend zone (Özel Not)')
    if t.get('short_direnc'):
        warnings.append(f'Short-term resistance: {" ".join(t["short_direnc"][:2])}')

    return len(rejects) == 0, rejects, warnings


def _score_sell(coin: str, sr: dict, ls: dict, t: dict) -> tuple[bool, list, list]:
    """Returns (passed, hard_rejects, soft_warnings) for a sell/short candidate."""
    rejects, warnings = [], []

    # LS: if 15m or 1h already bullish, NLS short exit fires immediately
    l15 = ls.get('15m')
    l1h = ls.get('1h')
    if l15 is not None and l15 > 55:
        rejects.append(f'15m Long={l15}% (buyers dominant — short exit fires immediately)')
    if l1h is not None and l1h > 55:
        rejects.append(f'1h Long={l1h}% (1h buyers dominant — risky short)')

    # Acc: panic buying = reject
    acc = sr.get('acc')
    if acc is not None:
        if acc > 5:
            rejects.append(f'Acc={acc} (panic buying — dangerous to short)')
        elif acc > 0:
            warnings.append(f'Acc={acc} (positive momentum)')

    # TrendString: warn if not in downtrend
    ts = (sr.get('trend_string') or '').replace(' ', '')
    if ts and not ts.startswith('-'):
        warnings.append(f'TrendString={ts} (not in downtrend)')

    # Volume: low volume = unreliable short signal
    vl = sr.get('vlast_v24h')
    if vl is not None:
        if vl < 0.5:
            rejects.append(f'VLast_V24H={vl} (very low volume — unreliable short)')
        elif vl < 1.0:
            warnings.append(f'VLast_V24H={vl} (below-average volume)')

    # HPriceInDay: at 24h high = good short entry (likely correction ahead)
    if sr.get('hprice_in_day') is True:
        warnings.append('HPriceInDay=True (at 24h high — good short entry)')

    # T: support nearby = coin may bounce before shorting
    if t.get('at_zone'):
        warnings.append('Price at trend zone')
    if t.get('short_destek'):
        warnings.append(f'Short-term support: {" ".join(t["short_destek"][:2])} (may bounce)')

    return len(rejects) == 0, rejects, warnings


# ── Deep-dive orchestrator ────────────────────────────────────────────────────

async def run_deepdive(buy_candidates: list, sell_candidates: list) -> dict:
    """
    Run sr + ls + t for every buy and sell candidate.
    Returns combined {coin: {sr, ls, t, passed, rejects, warnings, mode}} dict.
    Updates global _deepdive_results.
    """
    global _deepdive_results
    results = {}

    all_jobs = [(c, 'buy') for c in buy_candidates] + [(c, 'sell') for c in sell_candidates]
    if not all_jobs:
        return results

    print(f'\n[DEEPDIVE] Starting deep-dive for {len(all_jobs)} coin(s)...')
    print(f'  BUY candidates:  {buy_candidates or "none"}')
    print(f'  SELL candidates: {sell_candidates or "none"}')

    for coin, mode in all_jobs:
        coin_lower = coin.lower()
        print(f'\n[DEEPDIVE] ── {coin} ({mode}) ──')

        sr_resp = await _run_coin_command(f'sr {coin_lower}')
        await asyncio.sleep(3)
        ls_resp = await _run_coin_command(f'ls {coin_lower}')
        await asyncio.sleep(3)
        t_resp  = await _run_coin_command(f't {coin_lower}')
        await asyncio.sleep(3)

        sr = _parse_sr(sr_resp)
        ls = _parse_ls(ls_resp)
        t  = _parse_t(t_resp)

        if mode == 'buy':
            passed, rejects, warnings = _score_buy(coin, sr, ls, t)
        else:
            passed, rejects, warnings = _score_sell(coin, sr, ls, t)

        results[coin] = {
            'sr': sr, 'ls': ls, 't': t,
            'passed': passed, 'rejects': rejects, 'warnings': warnings,
            'mode': mode,
        }

        status = '✅ PASS' if passed else '❌ FAIL'
        print(f'[DEEPDIVE] {coin}: {status}')
        for r in rejects:   print(f'  REJECT: {r}')
        for w in warnings:  print(f'  WARN:   {w}')

    _deepdive_results = results
    return results


# ── Deep-dive Telegram message ────────────────────────────────────────────────

def _format_deepdive_msg(results: dict) -> str:
    ts = datetime.now().strftime('%H:%M')
    lines = [f'🔬 *Deep-Dive [{ts}]*\n']

    buy_coins  = {c: d for c, d in results.items() if d['mode'] == 'buy'}
    sell_coins = {c: d for c, d in results.items() if d['mode'] == 'sell'}

    first_section = True
    for section_label, section in [('📈 BUY', buy_coins), ('📉 SELL', sell_coins)]:
        if not section:
            continue
        if not first_section:
            lines.append('')
        first_section = False
        lines.append(f'*{section_label}*')
        for coin, d in section.items():
            sr, ls = d['sr'], d['ls']
            icon = '✅' if d['passed'] else '❌'
            ts_str  = sr.get('trend_string') or '?'
            acc     = sr.get('acc',        '?')
            mts     = sr.get('mts',        '?')
            vl      = sr.get('vlast_v24h', '?')
            l15     = ls.get('15m',        '?')
            l1h     = ls.get('1h',         '?')
            l4h     = ls.get('4h',         '?')
            at_zone = '⚡' if d['t'].get('at_zone') else ''
            lines.append(
                f'{icon} *{coin}*{at_zone}  TS:`{ts_str}`  Acc:`{acc}`  MTS:`{mts}`  Vol:`{vl}x`\n'
                f'   LS 15m:`{l15}%`  1h:`{l1h}%`  4h:`{l4h}%`'
            )
            if d['rejects']:
                lines.append('   🚫 ' + ' | '.join(d['rejects']))
            if d['warnings']:
                lines.append('   ⚠️ ' + ' | '.join(d['warnings']))

    # Summary line
    confirmed_buy  = [c for c, d in buy_coins.items()  if d['passed']]
    confirmed_sell = [c for c, d in sell_coins.items() if d['passed']]
    rejected_buy   = [c for c, d in buy_coins.items()  if not d['passed']]
    rejected_sell  = [c for c, d in sell_coins.items() if not d['passed']]

    lines.append('')
    if confirmed_buy:   lines.append(f'✅ BUY confirmed: *{", ".join(confirmed_buy)}*')
    if confirmed_sell:  lines.append(f'✅ SELL confirmed: *{", ".join(confirmed_sell)}*')
    if rejected_buy:    lines.append(f'❌ BUY rejected: {", ".join(rejected_buy)}')
    if rejected_sell:   lines.append(f'❌ SHORT rejected: {", ".join(rejected_sell)}')
    if not confirmed_buy and not confirmed_sell:
        lines.append('_No coins confirmed after deep-dive._')

    return '\n'.join(lines)


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
        bp_note = "WEAK — avoid new longs" if buy_power < 0.8 else ("STRONG — good for entries" if buy_power > 1.5 else "moderate")
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
    ssr_tradeable = [(s, d) for s, d in ssr.items() if d['ss'] > 5]
    ssr_tradeable.sort(key=lambda x: -x[1]['ss'])
    for sym, d in ssr_tradeable:
        ls = bls.get(sym, {})
        ls_score = ls.get('score', '?')
        vol = ls.get('vol', 0.0)
        in_dh = sym in dayhigh
        is_weak = sym in weak
        flags = []
        if d['mts'] >= 1.5:
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
    lines.append("=== WEAKCOIN LIST (do not trade in any direction) ===")
    lines.append("  " + ", ".join(sorted(weak)[:15]))

    sc_lines = [l for l in _lines('strongcoin') if l.strip()][:10]
    if sc_lines:
        lines.append("")
        lines.append("=== STRONGCOIN (currently trending upward — confirm with SSR before trading) ===")
        lines.extend(sc_lines)

    ci_lines = [l for l in _lines('ci s2 d') if l.strip()][:10]
    if ci_lines:
        lines.append("")
        lines.append("=== CI S2 D (coins that resist BTC drops and rise with BTC — IncScore > 1.05 is bullish) ===")
        lines.extend(ci_lines)

    # ── Deep-dive results (injected after each cycle) ──────────────────────
    if _deepdive_results:
        lines.append("")
        lines.append("=== DEEP-DIVE RESULTS (sr + ls + t per coin — run after monitor cycle) ===")
        lines.append("These are the CONFIRMED candidates after per-coin deep analysis.")

        confirmed_buy  = [c for c, d in _deepdive_results.items() if d['mode'] == 'buy'  and d['passed']]
        confirmed_sell = [c for c, d in _deepdive_results.items() if d['mode'] == 'sell' and d['passed']]
        rejected       = [c for c, d in _deepdive_results.items() if not d['passed']]

        if confirmed_buy:
            lines.append(f"CONFIRMED BUY: {', '.join(confirmed_buy)}")
            for coin in confirmed_buy:
                d  = _deepdive_results[coin]
                sr = d['sr']
                ls = d['ls']
                t  = d['t']
                lines.append(
                    f"  {coin}: TrendStr={sr.get('trend_string')}  Acc={sr.get('acc')}  "
                    f"MTS={sr.get('mts')}  Vol={sr.get('vlast_v24h')}x  "
                    f"LS(15m/1h/4h)={ls.get('15m')}%/{ls.get('1h')}%/{ls.get('4h')}%  "
                    f"AtZone={t.get('at_zone')}"
                )
                if d['warnings']:
                    lines.append(f"    Warnings: {' | '.join(d['warnings'])}")

        if confirmed_sell:
            lines.append(f"CONFIRMED SHORT: {', '.join(confirmed_sell)}")
            for coin in confirmed_sell:
                d  = _deepdive_results[coin]
                sr = d['sr']
                ls = d['ls']
                lines.append(
                    f"  {coin}: TrendStr={sr.get('trend_string')}  Acc={sr.get('acc')}  "
                    f"MTS={sr.get('mts')}  LS(15m/1h)={ls.get('15m')}%/{ls.get('1h')}%"
                )
                if d['warnings']:
                    lines.append(f"    Warnings: {' | '.join(d['warnings'])}")

        if rejected:
            lines.append(f"REJECTED (failed deep-dive): {', '.join(rejected)}")
            for coin in rejected:
                d = _deepdive_results[coin]
                lines.append(f"  {coin}: {' | '.join(d['rejects'])}")

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
                    "Using ONLY the data above (do not invent numbers), answer using Telegram markdown "
                    "(bold = *text*, italic = _text_):\n\n"
                    "*MARKET:* Is it Safe / Neutral / Risky? One sentence citing AP long-term value and buy power.\n\n"
                    "*BUY:* From the CONFIRMED BUY list in deep-dive results (if available), list each coin on its own line "
                    "with its key metrics (TrendString, Acc, MTS, Vol, LS 15m/1h). Bold each coin name like *ETH*. "
                    "If no deep-dive data, use SSR+BLS criteria. Note any warnings for each coin on the same line. No limit.\n\n"
                    "*SELL:* From the CONFIRMED SHORT list in deep-dive results (if available), list each coin on its own line "
                    "with its metrics. Bold each coin name like *PORTAL*. If no deep-dive data, use MTS>=1.5 AND BLS<=2 criteria. No limit.\n\n"
                    "*AVOID:* List each coin to avoid on its own line with the exact rejection reason. "
                    "Bold each coin name like *ALT*. Coins to avoid include those rejected by deep-dive or in the weakcoin list.\n\n"
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


async def notify_self(analysis: str, deepdive_section: str = ''):
    ts = datetime.now().strftime('%H:%M')
    text = f"📊 *MikaBot Analysis [{ts}]*\n\n{analysis}"
    if deepdive_section:
        text += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{deepdive_section}"
    try:
        await client.send_message('me', text, parse_mode='md')
    except Exception as e:
        print(f"[notify] Failed to send self-message: {e}")


# ── Command runner ───────────────────────────────────────────────────────────

async def run_command(command: str, wait: int = 10):
    for attempt in range(2):
        _buffer.clear()
        print(f"[{datetime.now().strftime('%H:%M')}] Fetching: {command}" + (" (retry)" if attempt else ""))
        await client.send_message(MIKABOT_USERNAME, command)
        await asyncio.sleep(wait)
        responses = list(_buffer)
        if responses:
            _save_log(command, responses)
            _display(command, responses)
            _market_snapshot[command] = responses
            return
        print(f"  [!] No response for '{command}'" + (" — skipping" if attempt else " — retrying..."))


# ── NLS exit alarm setup ─────────────────────────────────────────────────────

def _get_buy_candidates() -> list:
    """Returns coins meeting KA-aligned buy criteria for NLS long alarm setup.
    Mirrors Kurnaz Avcı logic: BLS=5 (+++++), PT>=1.0, TS<1.0, MTS<1.5, SS>5, not weakcoin.
    TS=NULL is allowed (e.g. ASTER). PT check skipped if coin not in KA response.
    Pattern check: skip if 15m+1h already bearish — alarm would fire immediately.
    """
    ssr  = _parse_ssreport()
    bls  = _parse_bestlongshort()
    weak = _parse_weakcoin()
    ka   = _parse_ka()

    candidates = []
    for sym, d in ssr.items():
        if sym in STABLECOINS:
            continue
        if sym in weak:
            continue
        if d['ss'] <= 5:
            continue
        if d['mts'] >= 1.5:
            continue
        bls_data = bls.get(sym, {})
        if bls_data.get('score', 0) < 5:
            continue
        ka_data = ka.get(sym, {})
        pt = ka_data.get('pt')
        if pt is not None and pt < 1.0:
            continue
        ts = d.get('ts')
        if ts is not None and ts >= 1.0:
            continue
        pattern = bls_data.get('pattern', 'xxxxx')
        if pattern[0] == '-' and pattern[1] == '-':
            continue
        candidates.append(sym)

    return candidates


async def setup_nls_alarms(confirmed_coins: list | None = None):
    """Send NLS exit alarm commands for confirmed buy candidates.
    If confirmed_coins provided (post-deep-dive), use that list.
    Otherwise fall back to _get_buy_candidates().
    """
    candidates = confirmed_coins if confirmed_coins is not None else _get_buy_candidates()
    new_alarms = [c for c in candidates if c not in _nls_alarms_sent]

    if not new_alarms:
        print('[NLS] No new buy candidates — no alarms to set.')
        return

    for coin in new_alarms:
        cmd = f'Nls {coin} {NLS_LONG_EXIT_PATTERN}:order futures %100 {coin}'
        print(f'[NLS] Setting exit alarm: {cmd}')
        await client.send_message(MIKABOT_USERNAME, cmd)
        _nls_alarms_sent.add(coin)
        await asyncio.sleep(2)

    lines = [f'• *{c}*  →  `Nls {c} {NLS_LONG_EXIT_PATTERN}:order futures %100 {c}`' for c in new_alarms]
    msg = (
        f'🔔 *NLS Buy Exit Alarms Set [{datetime.now().strftime("%H:%M")}]*\n\n'
        + '\n'.join(lines)
        + '\n\n_Auto-closes 100% of futures position when 15m + 1h turn bearish_'
    )
    await client.send_message('me', msg, parse_mode='md')
    print(f'[NLS] {len(new_alarms)} alarm(s) set: {", ".join(new_alarms)}')


# ── NLS short alarm setup ────────────────────────────────────────────────────

def _get_short_candidates() -> list:
    """Returns coins meeting sell/short criteria for NLS short alarm setup."""
    ssr  = _parse_ssreport()
    bls  = _parse_bestlongshort()
    weak = _parse_weakcoin()

    candidates = []
    for sym, d in ssr.items():
        if sym in STABLECOINS:
            continue
        if sym in weak:
            continue
        if d['ss'] <= 5:
            continue
        bls_data = bls.get(sym, {})
        bls_score = bls_data.get('score', 0)
        if d['mts'] < 1.5:
            continue
        if bls_score > 2:
            continue
        pattern = bls_data.get('pattern', 'xxxxx')
        if pattern[0] == '+' and pattern[1] == '+':
            continue
        candidates.append(sym)

    return candidates


async def setup_nls_short_alarms(confirmed_coins: list | None = None):
    """Send NLS short exit alarm commands for confirmed sell candidates.
    If confirmed_coins provided (post-deep-dive), use that list.
    Otherwise fall back to _get_short_candidates().
    """
    candidates = confirmed_coins if confirmed_coins is not None else _get_short_candidates()
    new_alarms = [c for c in candidates if c not in _nls_short_alarms_sent]

    if not new_alarms:
        print('[NLS SELL] No new sell candidates — no alarms to set.')
        return

    for coin in new_alarms:
        cmd = f'Nls {coin} {NLS_SHORT_EXIT_PATTERN}:order futures %100 {coin}'
        print(f'[NLS SELL] Setting exit alarm: {cmd}')
        await client.send_message(MIKABOT_USERNAME, cmd)
        _nls_short_alarms_sent.add(coin)
        await asyncio.sleep(2)

    lines = [f'• *{c}*  →  `Nls {c} {NLS_SHORT_EXIT_PATTERN}:order futures %100 {c}`' for c in new_alarms]
    msg = (
        f'📉 *NLS Sell Exit Alarms Set [{datetime.now().strftime("%H:%M")}]*\n\n'
        + '\n'.join(lines)
        + '\n\n_Auto-closes 100% of futures sell when 15m + 1h turn bullish_'
    )
    await client.send_message('me', msg, parse_mode='md')
    print(f'[NLS SELL] {len(new_alarms)} alarm(s) set: {", ".join(new_alarms)}')


# ── Clock alignment ──────────────────────────────────────────────────────────

def seconds_until_next_30min() -> float:
    """Returns seconds until the next :00 or :30 boundary."""
    now = datetime.now()
    total_seconds = now.minute * 60 + now.second + now.microsecond / 1_000_000
    elapsed_in_interval = total_seconds % MONITOR_INTERVAL
    if elapsed_in_interval == 0:
        return 0.0
    return MONITOR_INTERVAL - elapsed_in_interval


# ── Main loop ────────────────────────────────────────────────────────────────

async def monitoring_loop():
    print("Market monitor running. Press Ctrl+C to stop.\n")
    print("Schedule: runs at every :00, :30\n")

    wait = seconds_until_next_30min()
    if wait > 0:
        next_run = (datetime.now() + timedelta(seconds=wait)).strftime('%H:%M')
        print(f"Running immediately, then syncing to clock boundaries (next: {next_run})\n")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M')}] Starting cycle...\n")

        # ── 1. Fetch all market data ─────────────────────────────────────────
        for command, wait in MONITOR_SCHEDULE.items():
            await run_command(command, wait=wait)
            await asyncio.sleep(5)

        # ── 2. Get preliminary candidates from market-wide screens ───────────
        buy_candidates  = _get_buy_candidates()
        sell_candidates = _get_short_candidates()
        print(f'\n[CANDIDATES] Buy: {buy_candidates or "none"}')
        print(f'[CANDIDATES] Sell: {sell_candidates or "none"}')

        # ── 3. Deep-dive: sr + ls + t for each candidate ─────────────────────
        confirmed_buy  = []
        confirmed_sell = []

        if buy_candidates or sell_candidates:
            dd_results = await run_deepdive(buy_candidates, sell_candidates)

            confirmed_buy  = [c for c, d in dd_results.items() if d['mode'] == 'buy'  and d['passed']]
            confirmed_sell = [c for c, d in dd_results.items() if d['mode'] == 'sell' and d['passed']]

            dd_msg = _format_deepdive_msg(dd_results)
        else:
            dd_msg = ''
            print('[DEEPDIVE] No candidates this cycle — skipping.')

        # ── 4. AI analysis (includes deep-dive results via _build_context) ────
        print("[AI] Running analysis...")
        analysis = analyze_market()
        print_analysis(analysis)
        await notify_self(analysis, deepdive_section=dd_msg)

        # ── 5. Set NLS alarms only for deep-dive-confirmed coins ──────────────
        await setup_nls_alarms(confirmed_buy   if (buy_candidates  or sell_candidates) else None)
        await setup_nls_short_alarms(confirmed_sell if (buy_candidates or sell_candidates) else None)

        # ── 6. Wait for next clock boundary ──────────────────────────────────
        wait = seconds_until_next_30min()
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
