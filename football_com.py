"""
football_com.py — Authentic Football.com Booking Client
Zero fake codes. Only displays codes confirmed by Football.com's server.
"""

import requests
import json

FOOTBALL_COM_API = "https://www.football.com/api/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.football.com",
    "Referer": "https://www.football.com/ng/"
}


def generate_football_com_code(legs):
    """
    Attempts to register selections on Football.com.
    NEVER returns a fake code. Only returns authentic server codes.
    """
    if not legs:
        return None, "No matches selected."

    selections = []
    for leg in legs:
        selections.append({
            "home": leg.get("home_team"),
            "away": leg.get("away_team"),
            "pick": leg.get("market_pick"),
            "odds": leg.get("est_odds")
        })

    # Call Football.com order booking endpoint
    url = f"{FOOTBALL_COM_API}/order/booking"
    payload = {
        "items": selections,
        "channel": "web",
        "currency": "NGN"
    }

    try:
        res = requests.post(url, headers=HEADERS, json=payload, timeout=6)
        if res.status_code == 200:
            data = res.json()
            code = data.get("data", {}).get("code") or data.get("data", {}).get("bookingCode")
            if code:
                return str(code).upper(), None
            else:
                return None, f"Football.com error: {data.get('message', 'Booking rejected')}"
        elif res.status_code in [403, 401]:
            return None, "Football.com blocked cloud datacenter IP. Use Option A (Fast Codes) or open directly in your browser."
        else:
            return None, f"Football.com HTTP {res.status_code}"
    except Exception as e:
        return None, f"Connection to Football.com timed out: {str(e)}"
