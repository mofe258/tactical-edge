"""
football_com.py — Authentic Football.com Booking Client
Strictly returns 3 values (code, direct_url, booked_games) on every return path.
Zero unpack errors.
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
    Guaranteed to always return exactly 3 values: (code, direct_url, booked_games)
    """
    if not legs:
        return None, "https://www.football.com/ng/", []

    booked_games = []
    for leg in legs:
        booked_games.append({
            "fixture": f"{leg.get('home_team')} vs {leg.get('away_team')}",
            "pick": leg.get("market_pick"),
            "odds": leg.get("est_odds", 1.25),
            "comp": leg.get("competition", "Football")
        })

    direct_url = "https://www.football.com/ng/betslip"

    # Attempt official API booking
    url = f"{FOOTBALL_COM_API}/order/booking"
    payload = {
        "items": [
            {"home": g["fixture"].split(" vs ")[0], "away": g["fixture"].split(" vs ")[1], "pick": g["pick"]}
            for g in booked_games
        ],
        "channel": "web",
        "currency": "NGN"
    }

    try:
        res = requests.post(url, headers=HEADERS, json=payload, timeout=5)
        if res.status_code == 200:
            data = res.json()
            code = data.get("data", {}).get("code") or data.get("data", {}).get("bookingCode")
            if code:
                return str(code).upper(), f"https://www.football.com/ng/betslip?code={code}", booked_games
    except Exception:
        pass

    # If cloud server is blocked by firewall, return None for code so no fake string is shown
    return None, direct_url, booked_games
