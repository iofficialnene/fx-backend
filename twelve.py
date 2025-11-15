# twelve.py

def get_confluence():
    """
    Returns a list of Forex pairs with confluence data.
    Each pair has 'Weekly', 'Daily', 'H4', 'H1' trends.
    You can replace this dummy data with your real confluence calculations.
    """
    data = [
        {
            "Pair": "EURUSD=X",
            "Confluence": {
                "Weekly": "Strong Bullish",
                "Daily": "Bullish",
                "H4": "Bullish",
                "H1": "Bullish"
            }
        },
        {
            "Pair": "GBPJPY=X",
            "Confluence": {
                "Weekly": "Bearish",
                "Daily": "Strong Bearish",
                "H4": "Bearish",
                "H1": "Bullish"
            }
        },
        {
            "Pair": "USDJPY=X",
            "Confluence": {
                "Weekly": "Bullish",
                "Daily": "Bullish",
                "H4": "Strong Bullish",
                "H1": "Bullish"
            }
        }
    ]
    return data
