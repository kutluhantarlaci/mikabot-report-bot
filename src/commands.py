DISCOVERY_COMMANDS = [
    # --- Core ---
    'home', 'help', 'egitim',

    # --- Market & Coins ---
    'ap', 'io', 'io btc', 'iof',
    'ka', 'ssreport', 'grio',
    'so2', 'orderbook', 'heatmap btc',
    'so btc', 'cit',
    'cash 1h', 'cash 1d', 'cash 15m',
    'activelongshort', 'toplongshort', 'toplongshort asc',
    'ci', 'ci s d', 'ci s1 d', 'ci s2 d', 'ci i d', 'ci d d',
    'ci s2 d 5m', 'ci s2 d 15m', 'ci s2 d 1h',
    'BestLongShort', 'MarketAnaliz',
    'inout', 'btc', 'pumpcorrection',
    'strongcoin', 'trendscore',
    'corr asc', 'corr desc',
    'weakcoin', 'dayhigh', 'coinintrend',
    'bestcorr', 'acc asc', 'acc',
    'volumeacc', 'volumeexp', 'altpower',
    'svi desc', 'svi asc', 'reportvolume', 'aisignal',

    # --- Egitim (Education) sub-commands ---
    'EYapayZeka', 'ETemel', 'ELongShort', 'EYeniyim', 'EKapsam',
    'EPumpDumpKanalı', 'E5DkAnalizi', 'EYenilikler',
    'ERoadMap', 'EMarketDeprem', 'EKorelasyonŞiddeti',
    'EOdemeKaydettirme', 'EInOut', 'EInOutFlow',
    'ESSR', 'ENls', 'EKurnazAvcı', 'EAi',
    '/EDetayliBilgi', '/EBaşvuru', '/ESinyalMotoru',
]

# Commands that require a coin symbol parameter — skipped in auto-discovery
PARAMETRIC_COMMANDS = [
    # ── Deep-dive (per-coin analysis) ──────────────────────────────────────
    'sr {coin}',              # Full Kripto Avcısı report: TrendString, Acc, MTS, SS, VLast_V24H,
                              #   VLast_VHigh, VolumePerc, SVI, TrendLevels, TrendLevels_Big,
                              #   Correlation_BTC, BestCorrSymbol, Ch1h/Ch6h/Ch24h/Ch1w, HPriceInDay
    'symbolreport {coin}',    # Alias for sr {coin}
    'ls {coin}',              # Per-coin long/short dominance: Short%/Long% for 15m/1h/4h/12h/1d (SPOT only)
    'longshort {coin}',       # Alias for ls {coin}
    't {coin}',               # Support/resistance levels: short-term + medium-term zones
    'trend {coin}',           # Alias for t {coin}

    # ── Alarms ─────────────────────────────────────────────────────────────
    'nls {coin} {pattern}',               # NLS alarm: pattern = [15m][1h][4h][12h][1d], chars: +/-/x
    'nls {coin} {pattern}:{order}',       # Alarm-linked order: fires order when pattern matches
    'nka {coin}',                         # Alert when Kurnaz Avcı recommends coin
    'nka {coin} {minutes}',               # Alert only if KA recommended coin for >= N minutes in last 2 days
    'delete nls {coin}',                  # Delete all NLS alarms (+ linked orders) for a coin
    'show nls',                           # Show all active NLS alarms
    'show nka',                           # Show all active NKA alarms

    # ── Orders (require Binance API key added via addapikey) ───────────────
    'addapikey {apikey} {secretkey}',     # Register Binance API key with MikaBot
    'order spot %{pct} {from} {to}',      # Spot order by % of free balance  e.g. 'order spot %50 usdt btc'
    'order spot q{amount} {from} {to}',   # Spot order by quantity            e.g. 'order spot q1000 usdt btc'
    'order futures %{pct} {coin}',        # Close futures position by %       e.g. 'order futures %100 btc'

    # ── Price levels ───────────────────────────────────────────────────────
    'ret {minPrice}-{maxPrice}',          # Fibonacci retracement levels
    'retLn {minPrice}-{maxPrice}',        # Logarithmic retracement levels
    'channelbender {symbol}',             # Channel analysis for a trading pair e.g. 'channelbender btcusdt'
]

# How often the monitor loop runs (seconds) — also used to update README
MONITOR_INTERVAL = 1800   # 30 minutes

# Market commands polled continuously — ordered by priority (least critical first, most critical last)
# Last commands are fetched most recently when AI analysis runs
MONITOR_SCHEDULE = {
    'strongcoin':     3,   # Trending strong coins — changes slowly
    'weakcoin':       3,   # Avoid list — changes slowly
    'ci s2 d':        3,   # Best coins: resist drops + rise with BTC
    'MarketAnaliz':   3,   # AI market analysis
    'inout':          3,   # Cash flow report
    'ap':             3,   # Altcoin power — critical buy/sell threshold
    'BestLongShort':  3,   # Buy/sell pressure per coin
    'dayhigh':        3,   # Coins hitting 24h highs — momentum
    'ssreport':       3,   # Smart Score Report — only trade coins here
    'ka':             3,   # Kurnaz Avcı coin recommendations — fetched last, freshest
}
