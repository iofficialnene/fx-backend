import yfinance as yf
import time

# list of (display name, preferred symbol, optional fallback symbols list)
PAIRS = [
    # Majors
    ("EUR/USD", "EURUSD=X", []),
    ("GBP/USD", "GBPUSD=X", []),
    ("USD/JPY", "JPY=X", []),
    ("USD/CHF", "CHF=X", []),
    ("USD/CAD", "CAD=X", []),
    ("AUD/USD", "AUDUSD=X", []),
    ("NZD/USD", "NZDUSD=X", []),

    # Minors
    ("EUR/GBP", "EURGBP=X", []),
    ("EUR/JPY", "EURJPY=X", []),
    ("GBP/JPY", "GBPJPY=X", []),
    ("CHF/JPY", "CHFJPY=X", []),
    ("AUD/JPY", "AUDJPY=X", []),
    ("NZD/JPY", "NZDJPY=X", []),
    ("GBP/CAD", "GBPCAD=X", []),
    ("EUR/AUD", "EURAUD=X", []),

    # Exotics
    ("USD/TRY", "TRY=X", []),
    ("USD/ZAR", "ZAR=X", []),
    ("USD/NOK", "NOK=X", []),
    ("USD/SEK", "SEK=X", []),
    ("USD/MXN", "MXN=X", []),

    # Metals (try a primary and a fallback)
    ("Gold", "XAUUSD=X", ["GC=F"]),
    ("Silver", "XAGUSD=X", ["SI=F"]),

    # Indices (these sometimes fail on yf.download; safe_fetch handles it)
    ("S&P 500", "^GSPC", ["^SPX"]),
    ("Dow Jones", "^DJI", []),
    ("Nasdaq", "^IXIC", ["^NDX"]),
    ("FTSE 100", "^FTSE", []),
    ("DAX", "^GDAXI", []),
]

# timeframes and their yfinance intervals
TF_MAP = {
    "Weekly": {"period": "3mo", "interval": "1wk"},
    "Daily":  {"period": "1mo", "interval": "1d"},
    "H4":     {"period": "60d", "interval": "4h"},
    "H1":     {"period": "14d", "interval": "1h"},
}

# helper: tries preferred symbol then fallbacks
def try_symbols(sym, fallbacks):
    symbols = [sym] + (fallbacks or [])
    for s in symbols:
        yield s

def safe_fetch_history(symbol, period, interval):
    """
    Try to fetch history for symbol; return DataFrame or None.
    Uses yf.Ticker(...).history which is sometimes more stable than yf.download in loops.
    """
    try:
        tk = yf.Ticker(symbol)
        df = tk.history(period=period, interval=interval, prepost=False, timeout=10)
        # small sleep to avoid rate limits
        time.sleep(0.25)
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None

def get_trend_for_symbol(symbol):
    """Compute trend strings for Weekly, Daily, H4, H1 for one symbol."""
    trends = {}
    for tf, opts in TF_MAP.items():
        df = safe_fetch_history(symbol, period=opts["period"], interval=opts["interval"])
        if df is None or "Close" not in df.columns or len(df["Close"]) < 2:
            trends[tf] = ""  # no data
            continue

        last = float(df["Close"].iloc[-1])
        prev = float(df["Close"].iloc[-2])
        if last == prev:
            trends[tf] = "Neutral"
        else:
            change = (last - prev) / prev
            # thresholds tuned to avoid tiny noise false strong signals
            if change > 0:
                trends[tf] = "Strong Bullish" if change > 0.003 else "Bullish"
            else:
                trends[tf] = "Strong Bearish" if change < -0.003 else "Bearish"

    return trends

def calculate_confluence(trends):
    """Return percentage and a short summary string."""
    vals = [v for v in trends.values() if v]
    if len(vals) < 1:
        return 0, "No Data"

    bull = sum(1 for v in vals if "Bull" in v)
    bear = sum(1 for v in vals if "Bear" in v)

    total = len(TF_MAP)
    # only count non-empty (we used len(vals))
    if bull == total:
        return 100, "Strong Bullish"
    if bear == total:
        return 100, "Strong Bearish"
    if bull >= 3:
        return 75, "Bullish Bias"
    if bear >= 3:
        return 75, "Bearish Bias"
    if bull == 2:
        return 50, "Mild Bullish"
    if bear == 2:
        return 50, "Mild Bearish"
    return 0, "No Clear Confluence"

def get_confluence():
    results = []
    for display, symbol, fallbacks in PAIRS:
        # attempt symbol + fallbacks
        trends = None
        used_symbol = None
        for s in try_symbols(symbol, fallbacks):
            trends = get_trend_for_symbol(s)
            # if we got at least one non-empty timeframe, accept this symbol
            if any(v for v in trends.values()):
                used_symbol = s
                break
        if trends is None:
            trends = {k: "" for k in TF_MAP.keys()}

        percent, summary = calculate_confluence(trends)

        results.append({
            "Pair": display,
            "Symbol": used_symbol or symbol,
            "Confluence": trends,
            "ConfluencePercent": percent,
            "Summary": summary
        })

    return results
