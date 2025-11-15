# strategy.py
import yfinance as yf
import pandas as pd
import time

EMA_PERIOD = 200

# Full list (majors, crosses, exotics, gold, indices)
PAIRS = [
    # majors
    ("EURUSD","EURUSD=X"),("GBPUSD","GBPUSD=X"),("USDJPY","USDJPY=X"),("USDCHF","USDCHF=X"),
    ("AUDUSD","AUDUSD=X"),("NZDUSD","NZDUSD=X"),("USDCAD","USDCAD=X"),
    # crosses / majors
    ("EURJPY","EURJPY=X"),("EURGBP","EURGBP=X"),("EURCHF","EURCHF=X"),("EURAUD","EURAUD=X"),
    ("EURNZD","EURNZD=X"),("GBPJPY","GBPJPY=X"),("GBPAUD","GBPAUD=X"),("GBPNZD","GBPNZD=X"),
    ("GBPCHF","GBPCHF=X"),("AUDJPY","AUDJPY=X"),("AUDNZD","AUDNZD=X"),("AUDCHF","AUDCHF=X"),
    ("NZDJPY","NZDJPY=X"),("NZDCHF","NZDCHF=X"),
    # exotics / others
    ("USDSGD","USDSGD=X"),("USDHKD","USDHKD=X"),("USDZAR","USDZAR=X"),("USDMXN","USDMXN=X"),
    ("USDTRY","USDTRY=X"),("USDCNH","USDCNH=X"),("USDNOK","USDNOK=X"),("USDSEK","USDSEK=X"),
    # metals & commodities (yfinance common tickers)
    ("XAUUSD","XAUUSD=X"),("XAGUSD","XAGUSD=X"),("WTI","CL=F"),
    # indices (Yahoo tickers)
    ("US30","^DJI"),("SPX500","^GSPC"),("NAS100","^IXIC"),("FTSE","^FTSE"),
    ("GER40","^GDAXI"),("N225","^N225"),("HIS","^HSI")
]

PAIR_TYPES = {
    "Majors": {p for p,_ in PAIRS if p in {"EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","NZDUSD","USDCAD"}},
    "Crosses": {"EURJPY","EURGBP","EURCHF","EURAUD","EURNZD","GBPJPY","GBPAUD","GBPNZD","GBPCHF","AUDJPY","AUDNZD","AUDCHF","NZDJPY","NZDCHF"},
    "Exotics": {"USDSGD","USDHKD","USDZAR","USDMXN","USDTRY","USDCNH","USDNOK","USDSEK"},
    "Metals": {"XAUUSD","XAGUSD"},
    "Commodities": {"WTI"},
    "Indices": {"US30","SPX500","NAS100","FTSE","GER40","N225","HIS"}
}

def clean_df(df):
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df

def ema_trend(df, period=EMA_PERIOD):
    """Returns 'Bullish'/'Bearish'/'Sideways' or None"""
    if df is None or df.empty or "Close" not in df.columns:
        return None
    ema = df["Close"].ewm(span=period, adjust=False).mean()
    last_close = df["Close"].iloc[-1]
    last_ema = ema.iloc[-1]
    if last_close > last_ema:
        return "Bullish"
    elif last_close < last_ema:
        return "Bearish"
    else:
        return "Sideways"

def fetch_symbol(symbol):
    """Fetch weekly, daily, 4h, 1h and close prices for sparkline (last 20 H4 closes)."""
    try:
        weekly = clean_df(yf.download(symbol, period="1y", interval="1wk", progress=False, auto_adjust=True))
        daily = clean_df(yf.download(symbol, period="6mo", interval="1d", progress=False, auto_adjust=True))
        four_h = clean_df(yf.download(symbol, period="2mo", interval="4h", progress=False, auto_adjust=True))
        one_h = clean_df(yf.download(symbol, period="14d", interval="1h", progress=False, auto_adjust=True))
        # Build sparkline data: prefer 4H close if available, else 1H close, else daily last 20
        prices = []
        if not four_h.empty:
            prices = four_h["Close"].tail(20).tolist()
        elif not one_h.empty:
            prices = one_h["Close"].tail(20).tolist()
        elif not daily.empty:
            prices = daily["Close"].tail(20).tolist()
        return weekly, daily, four_h, one_h, prices
    except Exception as e:
        # don't crash — return empty frames
        print(f"fetch_symbol error for {symbol}: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), []

def confidence_pct(weekly, daily, h4, h1):
    """Confidence % measured as how many tf show same Bullish/Bearish (ignore Sideways/None)."""
    vals = []
    for v in (weekly, daily, h4, h1):
        if v in ("Bullish", "Bearish"):
            vals.append(v)
    if not vals:
        return 0
    # majority match
    bullish = vals.count("Bullish")
    bearish = vals.count("Bearish")
    top = max(bullish, bearish)
    return int(round(top / len(vals) * 100))

def run_confluence():
    results = []
    for label, symbol in PAIRS:
        weekly, daily, h4, h1, prices = fetch_symbol(symbol)
        w = ema_trend(weekly)
        d = ema_trend(daily)
        f4 = ema_trend(h4)
        o1 = ema_trend(h1)
        # status logic: strong if weekly==daily==4h and not None and not Sideways
        status = "❌ No Data"
        if w is None and d is None and f4 is None and o1 is None:
            status = "❌ No Data"
        else:
            if w == d == f4 and w in ("Bullish","Bearish"):
                status = f"✅ Strong {w}"
            else:
                # if 3 of 4 agree (majority), show "Aligned" maybe
                vals = [x for x in (w,d,f4,o1) if x in ("Bullish","Bearish")]
                if vals and (vals.count(vals[0]) >= 3 or max(vals.count("Bullish"), vals.count("Bearish")) >= 3):
                    # 3 out of 4 same
                    majority = "Bullish" if vals.count("Bullish") > vals.count("Bearish") else "Bearish"
                    status = f"⚠️ Mostly {majority}"
                else:
                    status = "❌ No Confluence"
        # type label
        ptype = next((k for k,s in PAIR_TYPES.items() if label in s), "Other")
        conf = confidence_pct(w,d,f4,o1)
        results.append({
            "pair": label,
            "symbol": symbol,
            "type": ptype,
            "status": status,
            "weekly": w,
            "daily": d,
            "four_hour": f4,
            "one_hour": o1,
            "confidence": conf,
            "prices": prices
        })
        # tiny sleep to be polite if many requests (prevents burst)
        time.sleep(0.1)
    return results

if __name__ == "__main__":
    # quick test run
    res = run_confluence()
    for r in res[:8]:
        print(r)
