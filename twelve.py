import yfinance as yf

PAIRS = [
    # Majors
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X",
    "AUDUSD=X", "USDCAD=X", "NZDUSD=X",
    # Minors
    "EURGBP=X", "EURJPY=X", "GBPJPY=X", "EURAUD=X", "GBPAUD=X",
    "AUDJPY=X", "AUDNZD=X",
    # Exotics
    "USDTRY=X", "USDMXN=X", "USDZAR=X", "USDHKD=X", "USDINR=X",
    # Indices
    "^DJI", "^GSPC", "^IXIC", "^FTSE", "^GDAXI", "^N225", "^HSI",
    # Commodities
    "GC=F", "CL=F", "SI=F"
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
                # Placeholder trends, replace with real logic if needed
                trends = {"Weekly": "Strong Bullish", "Daily": "Bullish", "H4": "Bullish", "H1": "Bearish"}

            confluence_count = sum(1 for t in trends.values() if t)
            percent = round((confluence_count / len(trends)) * 100)

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
