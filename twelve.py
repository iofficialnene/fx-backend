import os
import requests
import pandas as pd

API_KEY = os.getenv("TWELVEDATA_API_KEY")
BASE_URL = "https://api.twelvedata.com/time_series"

def get_candles(pair, interval):
    params = {
        "symbol": pair,
        "interval": interval,
        "apikey": API_KEY,
        "outputsize": 50
    }

    r = requests.get(BASE_URL, params=params).json()

    if "values" not in r:
        print("API ERROR:", r)
        return None

    df = pd.DataFrame(r["values"])
    df["open"] = df["open"].astype(float)
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    return df
