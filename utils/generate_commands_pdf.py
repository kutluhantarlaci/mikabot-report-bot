"""
Generate MikaBot Commands Reference PDF.
Uses pdf_knowledge.json + commands.py as source of truth.
"""
import json
import os as _os

# Resolve paths relative to project root (parent of utils/)
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# ── Emoji → safe symbol replacements ─────────────────────────────────────────
_EMOJI_MAP = {
    '🔼': '▲', '🔻': '▼',
    '⚠️': '[!]', '⚠': '[!]',
    '✅': '✓', '❌': '✗',
    '📈': '↑', '📉': '↓',
    '🔔': '[~]', '🔬': '[~]',
}

def _safe(text: str) -> str:
    for emoji, r in _EMOJI_MAP.items():
        text = text.replace(emoji, r)
    return text

# Patch Paragraph — auto-sanitise plain text, leave HTML intact
_OrigParagraph = Paragraph
class Paragraph(_OrigParagraph):
    def __init__(self, text, style, *args, **kwargs):
        t = str(text)
        if '<' not in t:
            t = _safe(t)
        super().__init__(t, style, *args, **kwargs)

# ── Register TrueType fonts ───────────────────────────────────────────────────
_FD = 'C:/Windows/Fonts'
pdfmetrics.registerFont(TTFont('Arial',           f'{_FD}/arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold',      f'{_FD}/arialbd.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Italic',    f'{_FD}/ariali.ttf'))
pdfmetrics.registerFont(TTFont('Courier-New',     f'{_FD}/cour.ttf'))
pdfmetrics.registerFont(TTFont('Courier-New-Bold',f'{_FD}/courbd.ttf'))
registerFontFamily('Arial', normal='Arial', bold='Arial-Bold',
                   italic='Arial-Italic', boldItalic='Arial-Bold')

# ── Load knowledge ────────────────────────────────────────────────────────────
with open(_os.path.join(_ROOT, 'data', 'pdf_knowledge.json'), 'r', encoding='utf-8') as f:
    kb = json.load(f)

# ── Colour palette ────────────────────────────────────────────────────────────
C_DARK   = colors.HexColor('#1a1a2e')
C_MID    = colors.HexColor('#16213e')
C_ACCENT = colors.HexColor('#0f3460')
C_GREEN  = colors.HexColor('#1a7a4a')
C_RED    = colors.HexColor('#8b1a1a')
C_LIGHT  = colors.HexColor('#f5f5f5')
C_WHITE  = colors.white
C_CMD_BG = colors.HexColor('#dce8fb')
C_EX_BG  = colors.HexColor('#f0f4f0')
C_EX_OUT = colors.HexColor('#3a3a3a')
C_CODE   = colors.HexColor('#1a1a2e')
C_LINK   = colors.HexColor('#1a5fcc')

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm

# ── Styles ────────────────────────────────────────────────────────────────────
S = {
    'title': ParagraphStyle('title',
        fontName='Arial-Bold', fontSize=26, textColor=C_DARK,
        spaceAfter=6, leading=32, alignment=TA_CENTER),

    'subtitle': ParagraphStyle('subtitle',
        fontName='Arial', fontSize=11, textColor=colors.HexColor('#444444'),
        spaceAfter=4, alignment=TA_CENTER),

    'section': ParagraphStyle('section',
        fontName='Arial-Bold', fontSize=13, textColor=C_WHITE,
        spaceBefore=14, spaceAfter=6, leading=18,
        backColor=C_MID, leftIndent=-MARGIN, rightIndent=-MARGIN,
        borderPad=(4, 8, 4, 8)),

    'subsection': ParagraphStyle('subsection',
        fontName='Arial-Bold', fontSize=10.5, textColor=C_DARK,
        spaceBefore=10, spaceAfter=3, leading=14),

    # ── Command block styles ──────────────────────────────────────────────────
    'cmd': ParagraphStyle('cmd',
        fontName='Courier-New-Bold', fontSize=10, textColor=C_CODE,
        backColor=C_CMD_BG, borderPad=(5, 8, 5, 8), leading=14,
        spaceBefore=6),

    'desc': ParagraphStyle('desc',
        fontName='Arial', fontSize=9.5, textColor=colors.HexColor('#1a1a1a'),
        leftIndent=10, spaceBefore=3, spaceAfter=2, leading=14),

    'bullets': ParagraphStyle('bullets',
        fontName='Arial', fontSize=9, textColor=colors.HexColor('#333333'),
        leftIndent=20, spaceBefore=1, spaceAfter=1, leading=13),

    'columns': ParagraphStyle('columns',
        fontName='Arial-Italic', fontSize=8.5,
        textColor=colors.HexColor('#555555'),
        leftIndent=10, spaceBefore=2, spaceAfter=2, leading=12),

    'ex_label': ParagraphStyle('ex_label',
        fontName='Arial-Bold', fontSize=8, textColor=colors.HexColor('#555555'),
        leftIndent=10, spaceBefore=4, spaceAfter=1, leading=11),

    'ex_cmd': ParagraphStyle('ex_cmd',
        fontName='Courier-New', fontSize=8.5, textColor=colors.HexColor('#0d3b8e'),
        backColor=C_EX_BG, leftIndent=14, borderPad=(3, 6, 2, 6), leading=12),

    'ex_out': ParagraphStyle('ex_out',
        fontName='Arial-Italic', fontSize=8, textColor=C_EX_OUT,
        leftIndent=24, spaceBefore=1, spaceAfter=3, leading=11),

    # ── Table styles ──────────────────────────────────────────────────────────
    'th': ParagraphStyle('th',
        fontName='Arial-Bold', fontSize=8.5, textColor=C_WHITE,
        alignment=TA_CENTER, leading=11),

    'td_key': ParagraphStyle('td_key',
        fontName='Courier-New-Bold', fontSize=8.5, textColor=C_CODE, leading=11),

    'td_val': ParagraphStyle('td_val',
        fontName='Arial', fontSize=8.5, textColor=colors.HexColor('#222222'),
        leading=12),

    'body': ParagraphStyle('body',
        fontName='Arial', fontSize=9, textColor=colors.HexColor('#222222'),
        spaceAfter=4, leading=13),

    'bullet': ParagraphStyle('bullet',
        fontName='Arial', fontSize=9, textColor=colors.HexColor('#222222'),
        leftIndent=14, spaceAfter=2, leading=13),
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def section_header(title: str) -> list:
    return [
        Spacer(1, 0.3 * cm),
        Paragraph(f'  {title}', S['section']),
        Spacer(1, 0.15 * cm),
    ]


def cmd_block(command: str, description: str,
              bullets: list = None,
              columns: str = '',
              examples: list = None) -> list:
    """
    command     — command syntax string (shown in code chip)
    description — one-line what-it-does
    bullets     — list of short bullet points for extra detail
    columns     — output column format note (italic)
    examples    — list of (cmd_str, explanation_str) tuples
    """
    items = [Paragraph(command, S['cmd'])]
    items.append(Paragraph(description, S['desc']))

    if bullets:
        for b in bullets:
            items.append(Paragraph(f'• {b}', S['bullets']))

    if columns:
        items.append(Paragraph(f'Columns: {columns}', S['columns']))

    if examples:
        items.append(Paragraph('Examples:', S['ex_label']))
        for ex in examples:
            if isinstance(ex, tuple):
                cmd_txt, out_txt = ex
                items.append(Paragraph(f'> {cmd_txt}', S['ex_cmd']))
                if out_txt:
                    items.append(Paragraph(out_txt, S['ex_out']))
            else:
                items.append(Paragraph(f'> {ex}', S['ex_cmd']))

    items.append(Spacer(1, 0.22 * cm))
    return items


def two_col_table(rows, col_widths=(5.5*cm, 11.5*cm), header=None) -> Table:
    data = []
    if header:
        data.append([Paragraph(header[0], S['th']),
                     Paragraph(header[1], S['th'])])
    for k, v in rows:
        data.append([Paragraph(k, S['td_key']),
                     Paragraph(v, S['td_val'])])
    tbl = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_ACCENT if header else C_WHITE),
        ('ROWBACKGROUNDS', (0, 1 if header else 0), (-1, -1), [C_LIGHT, C_WHITE]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return tbl


# ══════════════════════════════════════════════════════════════════════════════
# CONTENT
# ══════════════════════════════════════════════════════════════════════════════
story = []

# ── Cover ─────────────────────────────────────────────────────────────────────
story.append(Spacer(1, 3 * cm))
story.append(Paragraph('MikaBot', S['title']))
story.append(Paragraph('Complete Command Reference', S['subtitle']))
story.append(Spacer(1, 0.4 * cm))
story.append(HRFlowable(width='100%', thickness=1.5, color=C_ACCENT))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph(
    'All commands, metrics, thresholds and strategies — extracted from official MikaBot documentation.',
    S['subtitle']))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph('Telegram bot: @tradermikabot', S['subtitle']))
story.append(PageBreak())


# ══════════════════════════════════════════════════════════════════════════════
# 1. MARKET OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
story += section_header('1.  Market Overview Commands')

story += cmd_block(
    'ap  /  altpower',
    'Altcoin power index — three values (0–100): short-term altcoin strength vs BTC, '
    'short-term altcoin strength overall, and long-term altcoin market strength.',
    bullets=[
        'Short-term > 95 → take profits on everything immediately',
        'Short-term < 5  → buy altcoins (if no bad news)',
        'Long-term > 95  → stay away from market for several days',
        'Long-term < 5   → long-term investment opportunity',
        'Long-term 5→20  → recovery phase, active trading begins',
    ],
    examples=[
        ('ap',
         'Kısa Vadede Btc\'ye Karşı Gücü: 55.7  |  Kısa Vadede Gücü: 49.4  |  Uzun Vadede Gücü: 13.7'),
    ]
)

story += cmd_block(
    'io  /  inout',
    'Full cash flow report for all coins. Shows market-wide buy power (X multiplier), '
    'total volume share, and per-coin net cash flow with directional arrows (▲▼) for each timeframe.',
    columns='SYMBOL  Nakit:%X  15m:%X  Mts:X  [15m/1h/4h/12h/1d arrows]',
    examples=[
        ('io',  'Shows all coins sorted by cash inflow. Market Buy Power: 0.4X  |  Volume share: 73.4%'),
        ('io btc', 'Filters to BTC group only — shows BTC-group buy power and cash flow'),
    ]
)

story += cmd_block(
    'iof',
    'Smart-sorted cash inflow ranking — coins with the strongest net money flowing in, '
    'ranked by inflow strength (X multiplier).',
    columns='Symbol  GirişGücü(X)  NakitGirişPayı(%X)  Pahalılık(MTS)  BLS-arrows',
    examples=[
        ('iof', 'AXLUSDT 8.9X  Payı:%0.5  Pahalılık:1.2  ▲▲▲▲▲'),
    ]
)

story += cmd_block(
    'MarketAnaliz',
    'AI-generated market summary text produced by MikaBot\'s own analysis engine.',
    examples=[
        ('MarketAnaliz', 'Returns 2–3 lines of Turkish-language AI market commentary'),
    ]
)

story += cmd_block(
    'grio',
    'Cash flow broken down by coin sector/category: USA, L1, ETF, POW, AI, MEME, etc. '
    'Shows which sectors money is flowing into or out of.',
    columns='Category  N.Payı  N.Gücü  Pahalılık  15m%/1h%/4h%/12h%/1d%',
    examples=[
        ('grio', 'AI N.Payı:%3.3  N.Gücü:0.45X  Pahalılık:0.82  ▼▼▲▼▼'),
    ]
)

story += cmd_block(
    'orderbook',
    'Order book depth analysis. Shows total buy depth (−3%) vs sell depth (+3%), '
    'their ratio, and coins with the healthiest order books (most liquid for trading).',
    columns='$SYMBOL => Depth($M)  B/S:ratio  NC/D:24h_change',
    examples=[
        ('orderbook',
         'Total Buy Depth: 177.8M$  |  Total Sell Depth: 127.7M$  |  Ratio: 1.39\n'
         '$BTC => 47.5M$  B/S:1.55  NC/D:+0.01'),
    ]
)

story += cmd_block(
    'heatmap btc',
    'BTCUSDT spot order book density map — shows price zones with the heaviest '
    'buy and sell wall concentrations (in $M), useful for identifying key levels.',
    examples=[
        ('heatmap btc',
         'Top buy zones: 59580–60250: 32.6M$  |  69660–70440: 19.0M$\n'
         'Top sell zones: 73650–74330: 15.5M$  |  81420–82170: 14.9M$'),
    ]
)

story += cmd_block(
    'reportvolume',
    'Volume dominance (market share) for all coins in both USDT and BTC pairs. '
    'Shows which coins dominate volume and compares their USDT vs BTC pair activity.',
    columns='Coin:$X  V%:X  BTC:USDT(VRatio):X  Acc:X,Y',
    examples=[
        ('reportvolume',
         'Coin:$BTC  V%:18.9  BTC:USDT(VRatio):NONE:1  Acc:NONE:1'),
    ]
)

story += cmd_block(
    'aisignal',
    'AI buy/sell signals for all tracked coins. Header shows total buy and sell signal '
    'counts and overall market risk level. Use the buy/sell ratio to gauge market direction.',
    bullets=[
        'Buy(N)/Sell(N) ratio in the header is the key market health indicator',
        '>4/5 sell signals = very risky market, sharpest drops happen here',
        '>2/3 buy signals  = greedy/overbought market',
        'If BTC gets a buy signal and market is not risky → look for dip entries in other coins',
    ],
    examples=[
        ('aisignal',
         'Yapay Zeka Sinyalleri Buy(5) Sell(18) — Piyasa Riskli! ▲\n'
         'XRPUSDT  Ş.Fiyat:0.824  AlımFiyatı:0.832  Kar:%-1.18'),
    ]
)

story += cmd_block(
    'cash 1h  /  cash 1d  /  cash 15m',
    'Net cash inflow and outflow per coin for the specified time period. '
    'Shows which coins attracted or lost money in that window.',
    examples=[
        ('cash 1h',
         'Toplam Net Giriş: -6.3M$\n'
         'ETH: +0.98M$   BTC: +0.53M$   SOL: +0.52M$\n'
         'USDC: -7.28M$  XLM: -1.18M$'),
    ]
)


# ══════════════════════════════════════════════════════════════════════════════
# 2. COIN RANKINGS
# ══════════════════════════════════════════════════════════════════════════════
story += section_header('2.  Coin Rankings Commands')

story += cmd_block(
    'ssreport  /  ssr',
    'Smart Score Report — lists coins sorted by SmartScore descending. '
    'THE primary filter: only trade coins on this list with SS > 5. '
    'Big rallies only come from SSR coins. Also appends current KA recommendations at the bottom.',
    bullets=[
        'SS > 5 required — never trade outside this list',
        'Lower MTS = cheaper coin = better entry price',
        'Higher SS = stronger overall signal',
    ],
    columns='Symbol  Price  TrendString  **SmartScore**  TrendScore  MinorTrendScore',
    examples=[
        ('ssreport',
         'XLMUSDT 0.2384  + + + + +  **48.30**  0.8  3.2\n'
         'BTCUSDT 73650   + + + - -  **39.17**  0.8  1.0'),
        ('ssr', 'Alias — same result as ssreport'),
    ]
)

story += cmd_block(
    'ka  (Kurnaz Avcı)',
    'Smart coin buy recommendations. Shows coins the KA algorithm currently considers '
    'the best buy opportunities, with key metrics and how long they have been recommended.',
    bullets=[
        'Dk = total minutes KA recommended this coin in the last 2 days (higher = stronger)',
        'Kar% = P&L since KA first recommended in current session',
        'PT ≥ 1.0 = reliable pump history — prefer these',
        'Allocate 10–20% of portfolio per recommendation',
    ],
    columns='SYMBOL  TS:X  MTS:X  PT:X  /  Dk:X  Kar:%',
    examples=[
        ('ka',
         'AXL  TS:0.3  MTS:1.2  PT:0.978\n'
         ' Dk:3  Kar:%0.2  [Chart link]'),
    ]
)

story += cmd_block(
    'BestLongShort  /  bls',
    'Buy/sell dominance across 5 timeframes for every coin in the MikaBot system. '
    'Score 0–5 counts how many timeframes have buyers dominant. '
    'Score 5 (+++++) means buyers dominate in ALL timeframes — the strongest buy signal.',
    bullets=[
        'Pattern order: [15m][1h][4h][12h][1d]',
        '+ = buyers dominant in that timeframe',
        '- = sellers dominant',
        'V% > 3% for reliable signal, V% > 1% minimum',
    ],
    columns='SYMBOLUSDT=>{SCORE} {PATTERN}  V%:{VOLUME}',
    examples=[
        ('BestLongShort',
         'DOGEUSDT=>6  +++++  V%:8.8\n'
         'SOLUSDT=>5   +-+++  V%:3.0\n'
         'SUIUSDT=>2   --+--  V%:1.2'),
        ('bls', 'Alias — same result'),
    ]
)

story += cmd_block(
    'toplongshort  /  tls',
    'Top 15 coins with the strongest buying dominance right now. '
    'The buying dominance percentage must exceed 55% to be considered a meaningful signal.',
    bullets=[
        'MarketBuyPower > 55% = strong buying — worth analysing further',
        'V% > 3% = sufficient volume to be reliable',
        'Combine with SSR to confirm the coin is tradeable',
    ],
    columns='Symbol=>MarketBuyPower  VolumePerc  VLast_V24H  Acc',
    examples=[
        ('toplongshort',
         'BLZUSDT=>54.6  V:%0.0  VLast:0.70  Acc:8.01\n'
         'NEARUSDT=>51.9  V:%4.6  VLast:1.82  Acc:18.20'),
        ('toplongshort asc', 'Top 15 coins with strongest SELLING dominance'),
    ]
)

story += cmd_block(
    'strongcoin  /  sc',
    'Coins with the strongest upward price trend right now. '
    'Changes slowly — use to identify which sectors are currently trending '
    '(e.g. if AI coins dominate, focus NKA alarms on AI coins).',
    examples=[
        ('strongcoin', 'Lists trending coins — check which categories appear most frequently'),
        ('sc', 'Alias'),
    ]
)

story += cmd_block(
    'weakcoin',
    'Coins in persistent downtrend. Avoid trading in ANY direction — '
    'neither long nor short. These coins are excluded from all strategies.',
    examples=[
        ('weakcoin', 'AIUSDT  PYRUSDT  GTCUSDT  SOLVUSDT  TLMUSDT  ...'),
    ]
)

story += cmd_block(
    'dayhigh  /  dh',
    'Coins that reached their 24h high within the last 1.5 hours. '
    'CAUTION: these coins just hit their peak and may correct. '
    'Better used as an EXIT signal for existing positions, not an entry signal.',
    columns='Symbol  Price  VLast_V24H  Acc  **MinorTrendScore**',
    examples=[
        ('dayhigh',
         'XMRUSDT  220.5  VLast:2.47  Acc:6.07  **1.1**\n'
         'LUNAUSDT 115.1  VLast:1.30  Acc:6.22  **1.3**'),
    ]
)

story += cmd_block(
    'pumpcorrection  /  pc',
    'Coins with the biggest corrections from their recent peak (4h, 24h, 1 week). '
    'Use with ls {coin} to detect if the correction is ending and buyers are returning.',
    columns='Symbol  Price  4h:%  24h:%  1w:%  SS:X  MTS:X',
    examples=[
        ('pumpcorrection',
         'WAVESUSDT 28.08  4h:%2  24h:%12  1w:%56  SS:0  MTS:0.4\n'
         'RADUSDT   5.137  4h:%1  24h:%11  1w:%47  SS:0  MTS:0.7'),
    ]
)

story += cmd_block(
    'trendscore',
    'Trend Score Report — categorises all coins into groups: '
    'strong uptrend, cheap coins in uptrend, sharp correction in uptrend, and consolidating.',
    examples=[
        ('trendscore',
         'Güçlü Yükseliş Yapanlar: DEXEUSDT 2.42  JSTUSDT 2.14  NEARUSDT 1.25\n'
         'Fiyatı Sıkışanlar (consolidating): TRXUSDT 1.14  BNBUSDT ...'),
    ]
)

story += cmd_block(
    'coinintrend  /  cit',
    'Lists coins currently sitting at a support or resistance level. '
    'Shows short-term and medium-term S/R zones for each coin.',
    examples=[
        ('coinintrend',
         'ETHUSDT  Price:2018  +++--\n'
         '  Short: Support 1996–2005  |  Resistance 2043–2053\n'
         '  Medium: Trend zone 2017–2042'),
    ]
)

story += cmd_block(
    'bestcorr',
    'Groups coins by movement similarity — coins in the same group move together '
    'because they share the same investor base.',
    examples=[
        ('bestcorr', 'Lists coin groups — e.g. [SOLUSDT, BONKUSDT, LINKUSDT] move similarly'),
    ]
)

story += cmd_block(
    'acc',
    'Coins with the most panic BUYING (highest positive Acc value). '
    'Acc > 5 = panic buying underway.',
    columns='Symbol  Price  **Acc**  VLast_V24H  VLast_VHigh  TrendString  MTS',
    examples=[
        ('acc',
         'XLMUSDT  0.2411  **19.1**  1.73  0.48  +++++  3.33\n'
         'AXLUSDT  0.0564  **10.7**  6.88  0.06  ++++- 1.24'),
        ('acc asc', 'Coins with most panic SELLING (most negative Acc)'),
    ]
)

story += cmd_block(
    'volumeacc',
    'Coins with the highest recent volume surge — how many times above their 24h average '
    'the current volume is (VLast_V24H ratio).',
    columns='Symbol  Price  **VLast_V24H**  VLast_VHigh  Acc  TrendString  TrendScore  MTS',
    examples=[
        ('volumeacc',
         'AXLUSDT  0.0564  **6.88**  0.06  10.72  ++++- 0.3  1.24\n'
         'STGUSDT  0.1801  **2.16**  0.07  5.07   +++++  1.0  1.50'),
        ('volumeexp', 'Coins with biggest volume explosion relative to their own history'),
    ]
)

story += cmd_block(
    'svi desc  /  svi asc',
    'Smart Volatility Index rankings. High SVI = sharp recent moves. '
    'Low SVI = coin is squeezing/consolidating — watch for potential breakout.',
    examples=[
        ('svi desc', 'Most volatile: XLMUSDT 20.21  |  VICUSDT 17.17  |  WLDUSDT 14.00'),
        ('svi asc', 'Most squeezed: USDCUSDT 0.02  |  JSTUSDT 1.23  — potential breakout candidates'),
    ]
)

story += cmd_block(
    'so2',
    'Social media coins — biggest increase in mention rate. '
    'High SentimentScore (>85) + trending price = strong community interest.',
    columns='Rank  $SYMBOL  SentimentScore  24hVolume  Trend  MTS',
    examples=[
        ('so2',
         '1- $ALLO => 86  V:0.64B$  T:▼  Mts:null\n'
         '3- $INJ  => 89  V:0.32B$  T:▲  Mts:1.7'),
        ('so btc', 'BTC social media: BTC => %30.3  Sentiment: %79  TrendArtışı%: 13▲'),
    ]
)

story += cmd_block(
    'corr asc  /  corr desc',
    'BTC correlation rankings. '
    'corr asc = most independent coins (low correlation, move on their own). '
    'corr desc = coins that move most with BTC (+1.00 = perfectly correlated).',
    columns='Symbol  Correlation(-1 to +1)  CorrTrendString',
    examples=[
        ('corr desc', 'BTCUSDT 1.00  |  SOLUSDT 0.98  |  LINKUSDT 0.96  |  DOGEUSDT 0.93'),
        ('corr asc',  'PSGUSDT -0.34  |  MBOXUSDT -0.30  |  JSTUSDT -0.19'),
    ]
)


# ══════════════════════════════════════════════════════════════════════════════
# 3. CORRELATION INTENSITY (CI)
# ══════════════════════════════════════════════════════════════════════════════
story += section_header('3.  Correlation Intensity (CI) Commands')

story.append(Paragraph(
    'CI = Korelasyon Şiddeti. Finds coins that react best to BTC moves. '
    'Default timeframe is 15m. Append 5m, 15m, or 1h to specify. '
    'Output columns: Symbol  IncScore  DecScore  VolumePerDay  MinorTrendScore',
    S['body']))
story.append(Paragraph(
    'IncScore 1.03 = rises 3% MORE than BTC when BTC rises.  '
    'DecScore 0.93 = falls 7% LESS than BTC when BTC drops.  '
    'Ideal: IncScore > 1.05 AND DecScore < 1.0.',
    S['columns']))
story.append(Spacer(1, 0.2 * cm))

ci_rows = [
    ('ci',          'Default — 15m, sorted by Smart Score (balanced, low risk) descending'),
    ('ci s d',      'Smart score highest first — best all-round, balanced risk'),
    ('ci s a',      'Smart score lowest first'),
    ('ci s1 d',     'Score1 highest — coins that RISE most with BTC (pump focus)'),
    ('ci s1 a',     'Score1 lowest'),
    ('ci s2 d',     'Score2 highest — resist BTC drops AND rise with BTC. BEST for safe entries'),
    ('ci s2 a',     'Score2 lowest (worst performers)'),
    ('ci i d',      'IncScore highest — strongest BTC rise response'),
    ('ci i a',      'IncScore lowest'),
    ('ci d d',      'DecScore highest — drops hardest with BTC'),
    ('ci d a',      'DecScore lowest — resists BTC drops most'),
    ('ci s2 d 5m',  'Score2 for last 5 minutes'),
    ('ci s2 d 15m', 'Score2 for last 15 minutes'),
    ('ci s2 d 1h',  'Score2 for last 1 hour'),
]
story.append(two_col_table(ci_rows, header=('Command', 'Description')))

story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph('Examples:', S['ex_label']))
story.append(Paragraph('> ci s2 d', S['ex_cmd']))
story.append(Paragraph(
    'REQUSDT  IncScore:0.94  DecScore:0.89  Vol/Day:302  MTS:1.6\n'
    'NBSUSDT  IncScore:1.03  DecScore:0.93  Vol/Day:41   MTS:null  — ideal: rises more, falls less',
    S['ex_out']))
story.append(Paragraph('> ci s2 d 5m', S['ex_cmd']))
story.append(Paragraph('Same ranking but based on last 5 minutes of price action', S['ex_out']))


# ══════════════════════════════════════════════════════════════════════════════
# 4. PER-COIN DEEP-DIVE
# ══════════════════════════════════════════════════════════════════════════════
story += section_header('4.  Per-Coin Deep-Dive Commands')

story.append(Paragraph(
    'Run all three commands for every candidate before entering a position. '
    'Never buy based on market-wide screens alone — the deep-dive can reveal '
    'hidden problems (downtrend, panic selling, price at resistance).',
    S['body']))
story.append(Spacer(1, 0.2 * cm))

story += cmd_block(
    'sr {coin}  /  symbolreport {coin}',
    'Full "Kripto Avcısı" (Crypto Hunter) per-coin report — the most comprehensive '
    'single-coin analysis command. Returns everything you need to evaluate an entry.',
    bullets=[
        'TrendString: is the coin actually in an uptrend? Reject if -----',
        'Acc: positive = bullish momentum, negative = selling pressure',
        'MTS: must be < 1.5 for a buy — confirms price is not overextended',
        'VLast_V24H: volume above average (>1) confirms real interest',
        'TrendLevels: shows if price is near support (good entry) or resistance (risky)',
        'HPriceInDay: True = at today\'s high — correction risk',
        'SVI: low value = coin is squeezing = potential breakout setup',
    ],
    columns=(
        'Price · TrendString · Acc · Ss(SmartScore) · MinorTrendScore · VLast_V24H · VLast_VHigh · '
        'VolumePerc · SVI · TrendLevels · TrendLevels_Big · Correlation_BTC · '
        'BestCorrSymbol · Ch1h% · Ch6h% · Ch24h% · Ch1w% · HPriceInDay · Low24H · High24H'
    ),
    examples=[
        ('sr eth',
         'Price:2017  TrendString:+++-–  Acc:3.2  Ss:9.18  MTS:1.0\n'
         'VLast_V24H:1.23  VLast_VHigh:0.36  VolumePerc:%6.7  SVI:4.2\n'
         'TrendLevels:(-)1996–2005  (+)2043–2053  Correlation_BTC:0.92\n'
         'Ch1h:-0.3%  Ch24h:+2.1%  HPriceInDay:False'),
        ('sr btc',  'Full report for BTC'),
        ('sr sol',  'Full report for SOL'),
    ]
)

story += cmd_block(
    'ls {coin}  /  longshort {coin}',
    'Per-coin long/short dominance report. Shows the balance of spot buyers vs sellers '
    'across all five timeframes. SPOT ONLY — futures pressure is NOT included.',
    bullets=[
        'Long > 55% in 15m, 1h AND 4h = strong buy signal',
        'If 15m or 1h turns negative → whales may be selling at the top',
        'After a crash: wait for 15m+1h+4h to show Long dominance before buying',
        'Used in NLS alarms to define entry/exit conditions',
    ],
    examples=[
        ('ls btc',
         'BTCUSDT LONG SHORT BASKINLIK RAPORU\n'
         '15m → Short:42% → Long:58% ▲\n'
         '1h  → Short:46% → Long:54% ▲\n'
         '4h  → Short:52% → Long:48% ▼\n'
         '12h → Short:51% → Long:49% ▼\n'
         '1d  → Short:50% → Long:50% —'),
        ('ls eth', 'Long/short breakdown for ETH'),
        ('ls arpa',
         'Example of divergence: ls shows buy pressure BUT sr shows TrendString:----- '
         'and Acc:-1.18 → do NOT buy despite apparent buy dominance'),
    ]
)

story += cmd_block(
    't {coin}  /  trend {coin}',
    'Support and resistance levels for a coin — both short-term and medium-term zones. '
    'Use for planning entries at support and exits at resistance.',
    bullets=[
        '(-) prefix = support zone below current price',
        '(+) prefix = resistance zone above current price',
        '(0) prefix = price is AT this zone right now — key decision point',
        'Leftmost values are the STRONGEST zones',
        'Use for staged (incremental) buying at each support level',
        'Set take-profit targets at medium-term resistance levels',
    ],
    examples=[
        ('t btc',
         'BTCUSDT Fiyat:44034\n'
         'Kısa vadede: (0) at zone  |  Direnç:44353–44593  46751–46991\n'
         'Orta vadede: Destek:35709–36402  42643–43336  |  Direnç:44723–45416'),
        ('t eth', 'Support/resistance for ETH'),
        ('t xrp',
         'XRPUSDT Fiyat:0.7750\n'
         'Kısa vadede: Direnç:0.7835–0.7898  0.7898–0.7962\n'
         'Orta vadede: Direnç:1.395–1.409  1.338–1.352'),
    ]
)


# ══════════════════════════════════════════════════════════════════════════════
# 5. ALARM COMMANDS
# ══════════════════════════════════════════════════════════════════════════════
story += section_header('5.  Alarm Commands')

story.append(Paragraph(
    'All alarms start with "n" and stay active for 3 days. '
    'Check active alarms with show nls / show nka and renew them before they expire.',
    S['body']))
story.append(Spacer(1, 0.15 * cm))

story += cmd_block(
    'nls {coin} {pattern}',
    'NLS (Long/Short) alarm — triggers a notification when the coin\'s long/short profile '
    'matches the specified pattern.',
    bullets=[
        'Pattern = 5 characters, one per timeframe: [15m][1h][4h][12h][1d]',
        '+  = buyers dominant in that timeframe',
        '-  = sellers dominant',
        'x  = don\'t care (any condition)',
        'Short form: trailing x\'s can be omitted  →  nls btc + = nls btc +xxxx',
        'nls btc xxxxx is pointless — fires immediately in all conditions',
        'Only works for coins with V% ≥ 0.5 (minimum volume)',
        'TIP: for high-leverage futures, use shorter timeframes (++ at 15m+1h only)',
    ],
    examples=[
        ('nls btc +++++', 'Alert when ALL 5 timeframes show buyers dominant for BTC'),
        ('nls eth +',     'Alert when 15m buyers dominant (short form of nls eth +xxxx)'),
        ('nls btc --xxx', 'Alert when 15m AND 1h sellers dominant (our long exit pattern)'),
        ('nls btc ++xxx', 'Alert when 15m AND 1h buyers dominant (our short exit pattern)'),
    ]
)

story += cmd_block(
    'nls {coin} {pattern}:{order}',
    'Alarm-linked order — automatically executes a trade order the moment the alarm triggers. '
    'Combines an NLS alarm with an order command using ":" as separator.',
    examples=[
        ('nls btc +++++:order futures %100 btc',
         'Close 100% of BTC short position when all 5 timeframes show buyers'),
        ('nls btc -----:order futures %100 btc',
         'Close 100% of BTC long position when all 5 timeframes show sellers'),
        ('nls eth +++++:order spot q1000 usdt eth',
         'Buy ETH with 1000 USDT when all timeframes buying'),
        ('nls io xxxx-:order spot %50 wif usdt',
         'Sell 50% of WIF when daily IO cash flow turns negative'),
        ('nls io xxxx+:order futures %100 avax',
         'Close AVAX short when daily IO turns positive'),
    ]
)

story += cmd_block(
    'nka {coin}',
    'NKA alarm — sends a private notification the moment Kurnaz Avcı recommends this coin. '
    'Set on coins you\'re watching so you don\'t miss the entry window.',
    examples=[
        ('nka eth',   'Alert when KA recommends ETH'),
        ('nka jup',   'Alert when KA recommends JUP'),
        ('nka jup 15',
         'Alert only when KA has recommended JUP for 15+ total minutes in last 2 days '
         '(stronger/more sustained signal)'),
        ('nka fet',   'Useful when AI coins are trending — set on multiple AI coins'),
    ]
)

story += cmd_block(
    'show nls  /  show nka',
    'View all currently active alarms, including any linked order commands.',
    examples=[
        ('show nls', 'Lists all active NLS alarms with their patterns and linked orders'),
        ('show nka', 'Lists all active NKA alarms'),
    ]
)

story += cmd_block(
    'delete nls {coin}',
    'Deletes all NLS alarms (and their linked orders) for the specified coin.',
    examples=[
        ('delete nls eth', 'Removes all NLS alarms set for ETH'),
        ('delete nls btc', 'Removes all NLS alarms set for BTC'),
    ]
)

story += cmd_block(
    'enls',
    'Requests the latest NLS education document from MikaBot — '
    'full alarm documentation with up-to-date syntax and examples.',
    examples=[
        ('enls', 'Bot responds with comprehensive NLS guide in Turkish'),
    ]
)


# ══════════════════════════════════════════════════════════════════════════════
# 6. ORDER COMMANDS
# ══════════════════════════════════════════════════════════════════════════════
story += section_header('6.  Order Commands  (requires Binance API key)')

story.append(Paragraph(
    'Orders can run standalone (execute immediately) or attached to an NLS alarm (execute when triggered). '
    'Minimum spot order: 10 USDT. Futures orders only CLOSE existing positions.',
    S['body']))
story.append(Spacer(1, 0.15 * cm))

story += cmd_block(
    'addapikey {apikey} {secretkey}',
    'Register your Binance API key with MikaBot. One-time setup. '
    'MikaBot responds with your account balance summary to confirm success.',
    bullets=[
        'Create API at: binance.com → API Management → "Oluşturulan API"',
        'Select HMAC symmetric encryption (system-generated)',
        'Enable ONLY: Spot+Margin Trading AND Futures (if needed)',
        'NEVER enable: Withdrawal, Internal Transfer, Universal Transfer',
        'IP restriction: Unrestricted',
        'Secret Key shown ONCE — save it before clicking Save',
    ],
    examples=[
        ('addapikey inRceGNj...3z7pNOl32VaD kAbxvTa5...kPQrdZ3',
         'MikaBot responds with account balance summary confirming success'),
    ]
)

story += cmd_block(
    'order spot %{pct} {from} {to}',
    'Spot market order using a percentage of your free balance. '
    'Only USDT ↔ coin conversions are supported.',
    examples=[
        ('order spot %50 usdt btc',  'Buy BTC using 50% of your free USDT'),
        ('order spot %100 usdt eth', 'Buy ETH using 100% of your free USDT'),
        ('order spot %50 btc usdt',  'Sell 50% of your free BTC back to USDT'),
        ('order spot %25 sol usdt',  'Sell 25% of your SOL'),
    ]
)

story += cmd_block(
    'order spot q{amount} {from} {to}',
    'Spot order using an exact quantity. '
    'If free balance is less than specified, executes with whatever is available.',
    examples=[
        ('order spot q1000 usdt btc',  'Buy BTC with exactly 1000 USDT'),
        ('order spot q500 usdt eth',   'Buy ETH with exactly 500 USDT'),
        ('order spot q0,01 btc usdt',  'Sell exactly 0.01 BTC (Turkish decimal: comma)'),
    ]
)

story += cmd_block(
    'order futures %{pct} {coin}',
    'Close a futures position by percentage. Works for long or short positions at any leverage. '
    'USDT is auto-appended — use coin name or full pair.',
    bullets=[
        'Only closes existing positions — cannot open new futures positions',
        '% only — no quantity (q) syntax for futures',
        'May error if position dropped below Binance minimum due to losses',
    ],
    examples=[
        ('order futures %100 btc',    'Close 100% of your BTCUSDT position (long or short)'),
        ('order futures %100 btcusdt','Same — USDT is auto-appended if omitted'),
        ('order futures %50 eth',     'Close 50% of your ETHUSDT position'),
        ('order futures %10 trb',     'Close 10% of TRBUSDT regardless of leverage or direction'),
    ]
)

story.append(Paragraph(
    '[!]  SECURITY: Never enable Withdrawal, Internal Transfer or Universal Transfer on your API key. '
    'These permissions allow third parties to move funds out of your account.',
    ParagraphStyle('warn', fontName='Arial-Bold', fontSize=9,
                   textColor=C_RED, backColor=colors.HexColor('#fff0f0'),
                   borderPad=6, leading=13, spaceAfter=8)))


# ══════════════════════════════════════════════════════════════════════════════
# 7. METRIC DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
story += section_header('7.  Metric Definitions')

metrics = [
    ('SmartScore (SS)',       'Multi-parameter score: volume, surge, panic intensity, volume share, divergence, TrendString. Only trade SS > 5.'),
    ('MinorTrendScore (MTS)', '1.0 = neutral. <1 = cheap/undervalued. >1 = overpriced. >1.5 = do not buy. >1.7 = wait for 1.3–1.5. Lower is better for entry.'),
    ('TrendScore (TS)',       'Long-term price divergence. <1.0 = long-term undervalued (prefer). >1.0 = overvalued. NULL = not in long-term tracking (acceptable).'),
    ('PumpTrust (PT)',        'Reliability of upward moves (KA only). ≥1.0 = reliable. <1.0 = unreliable — caution or skip.'),
    ('TrendString',           '5 chars, LEFT = most recent. + = buyers dominant, - = sellers.\n'
                              '  +++++ strong uptrend  ·  ----- strong downtrend\n'
                              '  -++++ uptrend with recent dip  ·  --+++ losing momentum\n'
                              '  +++-- uptrend but medium-term selling starting'),
    ('BLS score',             '0–5 count of timeframes with buyers dominant. 5=+++++ = all buying. Order: [15m][1h][4h][12h][1d].'),
    ('MarketBuyPower (tls)',  '>55% = strong buy pressure. <50% = mixed or selling dominant.'),
    ('Acc',                   'Price acceleration/impulse. >5 = panic buying. <−5 = panic selling. Positive = bullish momentum.'),
    ('VLast_V24H',            'Volume last period / 24h average. >1 = above average. 2–3 = significant surge. <0.5 = very low — signal less reliable.'),
    ('VLast_VHigh',           'Volume last period / 10-day peak. >0.3 = good explosion. >0.5 = very strong. Near 1.0 = approaching 10-day peak volume.'),
    ('VInLast',               'Actual raw volume in last period (millions USD).'),
    ('VolumePerc (V%)',       '>3% = significant and reliable. >1% = minimum acceptable. ≥0.5% = required for NLS alarms.'),
    ('SVI',                   'Smart Volatility Index. Higher = more volatile/sharp moves. Lower = squeezing/consolidating = potential breakout.'),
    ('HPriceInDay',           'True = coin reached today\'s 24h high in last 1.5h. Momentum signal but also correction risk.'),
    ('TrendLevels',           'SHORT-TERM support/resistance. (+) = resistance, (−) = support, (0) = price at this zone now. Leftmost = strongest.'),
    ('TrendLevels_Big',       'MEDIUM-TERM support/resistance. Same format. Use for swing trade planning.'),
    ('Correlation_BTC',       '−1 to +1. +1 = moves perfectly with BTC. −1 = perfectly opposite. 0 = fully independent.'),
    ('BestCorrSymbol',        'The coin that moves most similarly to this one (shared investor base).'),
    ('IncScore (CI)',          'How much coin rises when BTC rises. 1.03 = rises 3% MORE than BTC. Target: >1.05.'),
    ('DecScore (CI)',          'How much coin falls when BTC falls. 0.93 = falls 7% LESS. Target: <1.0 (resists drops).'),
    ('Score2 (ci s2)',         'Rewards coins that resist BTC drops (low DecScore) AND rise with BTC (high IncScore). Best for safe entries.'),
    ('Dk (KA field)',          'Total minutes KA has recommended this coin in last 2 days. Higher = more sustained recommendation.'),
    ('Kar% (KA field)',        'P&L% since KA first recommended this coin in current session.'),
    ('BuyPower X (inout)',     '<0.8X = weak market. 0.8–1.5X = moderate. >1.5X = strong — good for new entries.'),
    ('Ch1h/Ch6h/Ch24h/Ch1w',  'Price change % over 1h, 6h, 24h, 1 week.'),
    ('Low24H / High24H',       '24h lowest/highest price. Near Low24H = near daily bottom. Near High24H = near daily top.'),
    ('RateCAndLastMax',        'Current price / recent max price. Tells you how much the coin corrected from its peak.'),
]
story.append(two_col_table(metrics, col_widths=(4.5*cm, 12.5*cm),
                           header=('Metric', 'Definition')))


# ══════════════════════════════════════════════════════════════════════════════
# 8. KEY THRESHOLDS
# ══════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
story += section_header('8.  Key Thresholds Quick Reference')

thresholds = [
    ('SS',                  '> 5  required to trade — never trade outside SSR list'),
    ('MTS buy',             '< 1.5  to buy   ·   1.3–1.5  ideal entry zone   ·   > 1.7  wait for pullback'),
    ('MTS short',           '≥ 1.5  potential short candidate'),
    ('BLS buy',             '= 5  (all 5 timeframes bullish, +++++)'),
    ('BLS sell',            '≤ 2  (sellers dominant in 3+ timeframes)'),
    ('PT',                  '≥ 1.0  reliable pump history  ·  < 1.0  caution'),
    ('TS',                  '< 1.0  long-term undervalued  ·  NULL = acceptable'),
    ('AP short-term sell',  '> 95  take ALL profits — whales realising'),
    ('AP short-term buy',   '< 5   buy altcoins (if no bad news)'),
    ('AP long-term avoid',  '> 95  stay away for several days'),
    ('AP long-term invest',  '< 5   long-term investment opportunity'),
    ('AP long-term active', '5→20  recovery phase — active trading begins'),
    ('AP long-term bull',   'Goes from < 5 to > 80 over months = altcoin bull season'),
    ('AP long-term bear',   'Goes from > 95 to < 20 over months = bear market confirmed'),
    ('BuyPower X weak',     '< 0.8X  weak market — avoid new longs'),
    ('BuyPower X strong',   '> 1.5X  strong market'),
    ('V% reliable',         '> 3%  significant  ·  > 1%  minimum  ·  ≥ 0.5%  for NLS alarms'),
    ('TopLongShort buy',    '> 55%  Long dominance = strong buy signal'),
    ('IncScore',            '> 1.05  strong BTC-rise candidate'),
    ('DecScore',            '< 1.0  resists BTC drops (lower is better)'),
    ('Acc panic buy',       '> 5'),
    ('Acc panic sell',      '< −5'),
    ('VLast_V24H',          '> 1  above average  ·  2–3  significant surge  ·  < 0.5  avoid'),
    ('VLast_VHigh',         '> 0.3  good explosion  ·  > 0.5  very strong'),
    ('Long % (ls)',         '> 55%  in 15m, 1h, 4h = strong spot buy signal'),
    ('Spot min order',      '10 USDT minimum (Binance restriction)'),
    ('Alarm duration',      '3 days — renew with show nls / show nka'),
]

thr_data = [[Paragraph('Metric / Condition', S['th']), Paragraph('Threshold', S['th'])]]
for k, v in thresholds:
    thr_data.append([Paragraph(k, S['td_key']), Paragraph(v, S['td_val'])])
thr_tbl = Table(thr_data, colWidths=[5*cm, 12*cm], repeatRows=1)
thr_tbl.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), C_ACCENT),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_LIGHT, C_WHITE]),
    ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#cccccc')),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('TOPPADDING', (0, 0), (-1, -1), 4),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
]))
story.append(thr_tbl)


# ══════════════════════════════════════════════════════════════════════════════
# 9. STRATEGIES
# ══════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
story += section_header('9.  Official MikaBot Strategies')

story.append(Paragraph('Strategy 1 — SSR Filter', S['subsection']))
story.append(Paragraph(
    'ONLY trade coins in the SSR (ssreport) list with SmartScore > 5. '
    'Big rallies only come from SSR coins. This is the single most important rule.',
    S['body']))

story.append(Paragraph('Strategy 2 — Kurnaz Avcı (KA)', S['subsection']))
for b in [
    'Allocate 10–20% of portfolio per KA recommendation.',
    'PT must not be much below 1.0 (reliable pump history required).',
    'If MTS > 1.7: wait for it to fall to 1.3–1.5 before buying.',
    'If a coin has a special narrative: start a position with nls xx- exit alarm even at high P&L.',
    'Set nka {coin} alarms for coins you are watching — get alerted when KA recommends.',
    'Use nka {coin} 15 for stronger signal (recommended for 15+ minutes recently).',
    'Find trending sectors with strongcoin → place NKA alarms on coins in that sector.',
    'Do NOT wait in dormant coins — use NKA alarms and deploy capital in active coins.',
]:
    story.append(Paragraph(f'• {b}', S['bullet']))

story.append(Paragraph('Strategy 3 — AP (Altcoin Power) Thresholds', S['subsection']))
ap_rows = [
    ('AP Short-term > 95',  'TAKE ALL PROFITS — whales realising gains, market overbought'),
    ('AP Short-term < 5',   'BUY altcoins (if no bad news in market)'),
    ('AP Long-term > 95',   'Stay away from market for several days'),
    ('AP Long-term < 5',    'Long-term investment opportunity (bear market bottom)'),
    ('AP Long 5→20',        'Recovery phase — active trading begins'),
    ('AP Long < 5 then > 80 (months)', 'Altcoin bull season — ideal time for altcoin investments'),
    ('AP Long 95 then < 20 (months)',  'Bear market officially entered'),
]
story.append(two_col_table(ap_rows, col_widths=[5.5*cm, 11.5*cm]))

story.append(Paragraph('Strategy 4 — Per-Coin Deep-Dive (before EVERY entry)', S['subsection']))
story.append(Paragraph(
    'Run all 3 commands for every candidate. Never buy based on market-wide screens alone.',
    S['body']))
for s in [
    'ls {coin} — Long must be >55% in 15m, 1h, 4h (SPOT only, no futures noise).',
    'sr {coin} — Check TrendString (reject -----), Acc (positive = bullish), VLast_V24H (>1 = volume present), '
    'MTS (<1.5), TrendLevels (at support or resistance?).',
    't {coin} — At support (good entry) or resistance (risky)? (0) = at zone now. '
    'Use support zones for staged/incremental buying.',
]:
    story.append(Paragraph(f'  {s}', S['bullet']))

story.append(Paragraph('Strategy 5 — AI Signal Chain (aisignal)', S['subsection']))
signal_rows = [
    ('>2/3 coins get sell signals',   'RISKY — no new buys, slowly move to cash'),
    ('>4/5 coins get sell signals',   'VERY RISKY — sharpest drops happen here'),
    ('>1/3 buy signals after crash',  'Risk reducing — start buying watched coins (early bottom catch)'),
    ('>2/3 coins get buy signals',    'GREEDY / overbought market'),
    ('All buy then sell >1/3',        'Strong bull ending — start reducing positions'),
    ('BTC gets buy signal, not risky','Look for OTHER coins without buy signals yet → dip entries'),
]
story.append(two_col_table(signal_rows, col_widths=[6*cm, 11*cm]))

story.append(Paragraph('Strategy 6 — BestLongShort Usage', S['subsection']))
for b in [
    'Coins about to pump almost always show Long dominant BEFORE the move.',
    'After a sharp drop: wait for 15m + 1h + 4h Long dominance before buying.',
    'Coin rising but 15m/1h flip to Short → whales selling at the top.',
    'Market weak but specific coin shows Long dominant → opportunity (confirm with CI and SR).',
]:
    story.append(Paragraph(f'• {b}', S['bullet']))


# ══════════════════════════════════════════════════════════════════════════════
# 10. SETUP & LINKS
# ══════════════════════════════════════════════════════════════════════════════
story += section_header('10.  Setup & Misc Commands')
misc_rows = [
    ('/start',          'Activate bot (first time only).'),
    ('home / HOME',     'Load main keyboard menu. Response: "Main Menu Loaded.."'),
    ('help',            'Full command reference in Turkish.'),
    ('egitim',          'Load education keyboard menu.'),
    ('getmi',           'View your membership/subscription info.'),
    ('vip',             'VIP membership information.'),
    ('pay',             'Payment for MikaBot subscription.'),
    ('problem',         'Report system issues. Format: problem "description"'),
    ('öneri',           'Submit feature suggestions.'),
]
story.append(two_col_table(misc_rows, col_widths=[5*cm, 12*cm], header=('Command', 'Description')))

story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph('Telegram Channels', S['subsection']))
links_rows = [
    ('Bot (commands)',
     '<a href="https://t.me/tradermikabot" color="#1a5fcc">t.me/tradermikabot</a>'),
    ('Notifications',
     '<a href="https://t.me/mikabotSinyal" color="#1a5fcc">t.me/mikabotSinyal</a>'
     '  — push alerts: rising coins + Market Deprem'),
    ('Public announcements',
     '<a href="https://t.me/mikabotPublic" color="#1a5fcc">t.me/mikabotPublic</a>'),
]
story.append(two_col_table(links_rows, col_widths=[5*cm, 12*cm]))

story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph('Video Tutorials', S['subsection']))
vid_rows = [
    ('Pump Hunter LongShort',
     '<a href="https://www.youtube.com/watch?v=_SZ3pR4w158" color="#1a5fcc">youtube.com/watch?v=_SZ3pR4w158</a>'),
    ('Finding Opportunity Coins',
     '<a href="https://www.youtube.com/watch?v=4jUvAv9AHFQ" color="#1a5fcc">youtube.com/watch?v=4jUvAv9AHFQ</a>'),
    ('Per-Coin Deep Query',
     '<a href="https://www.youtube.com/watch?v=Qd9ZFefPRD8" color="#1a5fcc">youtube.com/watch?v=Qd9ZFefPRD8</a>'),
    ('Detecting Buying After Crash',
     '<a href="https://www.youtube.com/watch?v=QtP9-hJQXig" color="#1a5fcc">youtube.com/watch?v=QtP9-hJQXig</a>'),
    ('CI in Bear Market',
     '<a href="https://www.youtube.com/watch?v=BhRiJjqZgmM" color="#1a5fcc">youtube.com/watch?v=BhRiJjqZgmM</a>'),
    ('Full Market Analysis Example',
     '<a href="https://www.youtube.com/watch?v=Kdto5jTJtAs" color="#1a5fcc">youtube.com/watch?v=Kdto5jTJtAs</a>'),
]
story.append(two_col_table(vid_rows, col_widths=[6*cm, 11*cm]))


# ══════════════════════════════════════════════════════════════════════════════
# Build PDF
# ══════════════════════════════════════════════════════════════════════════════

def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont('Arial', 7.5)
    canvas.setFillColor(colors.HexColor('#888888'))
    canvas.drawString(MARGIN, 0.8 * cm, 'MikaBot Command Reference')
    canvas.drawRightString(PAGE_W - MARGIN, 0.8 * cm, f'Page {doc.page}')
    canvas.restoreState()


out = _os.path.join(_ROOT, 'assets', 'mikabot_commands_reference.pdf')
doc = SimpleDocTemplate(
    out, pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    title='MikaBot Command Reference',
    author='MikaBot Monitor',
)
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f'PDF generated: {out}')
