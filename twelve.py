import yfinance as yf

# List of all pairs, indices, and gold
PAIRS = [
    # Majors
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X",
    "AUDUSD=X", "USDCAD=X", "NZDUSD=X",
    # Minors
    "EURGBP=X", "EURJPY=X", "GBPJPY=X",
    # Exotics
    "USDTRY=X", "USDMXN=X", "USDZAR=X",
    # Indices
    "^DJI", "^GSPC", "^IXIC", "^FTSE", "^GDAXI",
    # Commodities
    "GC=F"  # Gold
]

def get_confluence():
    results = []
    for symbol in PAIRS:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                trends = {"Weekly": "", "Daily": "", "H4": "", "H1": ""}
            else:
                # Example logic; replace with real trend calculation if you have it
                trends = {"Weekly": "Strong Bullish", "Daily": "Bullish", "H4": "Bullish", "H1": "Bearish"}

            confluence_count = sum(1 for t in trends.values() if t)
            total = len(trends)
            percent = round((confluence_count / total) * 100)

            results.append({
                "Pair": symbol.replace("=X","").replace("USD","/USD"),
                "Symbol": symbol,
                "Confluence": trends,
                "ConfluencePercent": percent,
                "Summary": "Example"
            })
        except Exception as e:
            results.append({
                "Pair": symbol.replace("=X","").replace("USD","/USD"),
                "Symbol": symbol,
                "Confluence": {"Weekly": "", "Daily": "", "H4": "", "H1": ""},
                "ConfluencePercent": 0,
                "Summary": f"No data ({str(e)})"
            })
    return results
