"""
sportybet.py — Automated SportyBet Booking Code Generator (Nigeria / Ghana / Kenya)
"""

import requests
import json

# Change base domain if Ghana (.com.gh) or Kenya (.co.ke)
SPORTYBET_API_BASE = "https://www.sportybet.com/api/ng"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://www.sportybet.com",
    "Referer": "https://www.sportybet.com/ng/"
}


def search_sportybet_event(team_name):
    """
    Searches SportyBet for the team name to extract SportyBet's internal eventId.
    """
    url = f"{SPORTYBET_API_BASE}/factsCenter/pcOrTabletsSearch"
    params = {"searchKey": team_name}
    try:
        res = requests.get(url, params=params, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            data = res.json()
            events = data.get("data", {}).get("events", [])
            if events:
                # Return first matching event
                return events[0]
    except Exception:
        pass
    return None


def map_market_to_sportybet(market_pick):
    """
    Maps your engine's pick to SportyBet market ID and outcome ID.
    SportyBet IDs:
    - 1X2: marketId = 1 (Home: outcomeId 1, Draw: 2, Away: 3)
    - Over/Under 1.5: marketId = 18, specifier = "total=1.5" (Over: 12, Under: 13)
    - Over/Under 2.5: marketId = 18, specifier = "total=2.5" (Over: 12, Under: 13)
    - Double Chance: marketId = 10 (1X: outcomeId 9, 12: 10, X2: 11)
    """
    p = market_pick.lower()

    if "home or draw" in p or "1x" in p:
        return {"marketId": "10", "outcomeId": "9", "specifier": None}
    if "draw or away" in p or "x2" in p:
        return {"marketId": "10", "outcomeId": "11", "specifier": None}
    if "over 1.5" in p:
        return {"marketId": "18", "outcomeId": "12", "specifier": "total=1.5"}
    if "over 2.5" in p:
        return {"marketId": "18", "outcomeId": "12", "specifier": "total=2.5"}
    if "under 3.5" in p:
        return {"marketId": "18", "outcomeId": "13", "specifier": "total=3.5"}
    if "home" in p and "win" in p:
        return {"marketId": "1", "outcomeId": "1", "specifier": None}
    if "away" in p and "win" in p:
        return {"marketId": "1", "outcomeId": "3", "specifier": None}

    # Default fallback: Over 1.5 Goals
    return {"marketId": "18", "outcomeId": "12", "specifier": "total=1.5"}


def generate_sportybet_code(legs):
    """
    Takes your selected match legs, maps them to SportyBet live fixtures,
    and calls SportyBet's /orders/share API to create a real booking code.
    """
    sporty_outcomes = []

    for leg in legs:
        home_team = leg["home_team"]
        # Search SportyBet event ID using home team
        event = search_sportybet_event(home_team)
        if not event:
            continue

        event_id = event.get("eventId")
        mapped_mkt = map_market_to_sportybet(leg["market_pick"])

        outcome_item = {
            "eventId": event_id,
            "marketId": mapped_mkt["marketId"],
            "outcomeId": mapped_mkt["outcomeId"]
        }
        if mapped_mkt["specifier"]:
            outcome_item["specifier"] = mapped_mkt["specifier"]

        sporty_outcomes.append(outcome_item)

    if not sporty_outcomes:
        return None, "Could not match selected games with SportyBet's live fixture IDs."

    # Send order to SportyBet's share endpoint
    url = f"{SPORTYBET_API_BASE}/orders/share"
    payload = {
        "outcomes": sporty_outcomes
    }

    try:
        res = requests.post(url, headers=HEADERS, json=payload, timeout=8)
        if res.status_code == 200:
            resp_data = res.json()
            code = resp_data.get("data", {}).get("shareCode")
            if code:
                return code, None
            return None, resp_data.get("message", "SportyBet rejected the booking request.")
        else:
            return None, f"SportyBet API error HTTP {res.status_code}"
    except Exception as e:
        return None, f"Network error connecting to SportyBet: {str(e)}"
