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
    'ci', 'BestLongShort', 'MarketAnaliz',
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
    '/EInOut', '/EInOutFlow', '/ETemel', '/ESSR', '/ENls',
    '/EYapayZeka', '/EDetayliBilgi', '/EBaşvuru', '/EMarketDeprem',
    '/EKurnazAvcı', '/EKurnazAvci', '/EkaAll', '/EAi', '/ESinyalMotoru',
]

# Commands that require a coin symbol parameter — skipped in auto-discovery
PARAMETRIC_COMMANDS = [
    'nls {coin} {character}',
    'ret {minPrice}-{maxPrice}',
    'retLn {minPrice}-{maxPrice}',
    'symbolreport {coin}',
    'channelbender {symbol}',
    'trend {coin}',
]

# Market commands polled continuously — ordered by priority (least critical first, most critical last)
# Each command takes ~15s, so last commands are freshest when AI analysis runs
MONITOR_SCHEDULE = {
    'strongcoin':     15,   # Trending strong coins — changes slowly
    'weakcoin':       15,   # Avoid list — changes slowly
    'ci s2 d':        15,   # Best coins: resist drops + rise with BTC
    'MarketAnaliz':   15,   # AI market analysis
    'inout':          15,   # Cash flow report
    'ap':             15,   # Altcoin power — critical buy/sell threshold
    'BestLongShort':  15,   # Buy/sell pressure per coin
    'dayhigh':        15,   # Coins hitting 24h highs — momentum
    'ssreport':       15,   # Smart Score Report — only trade coins here
    'ka':             15,   # Kurnaz Avcı coin recommendations — fetched last, freshest
}
