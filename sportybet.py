"""
sportybet.py — Official Direct SportyBet Order Dispatcher
Books directly using SportyBet's pre-verified internal eventId.
"""

import requests
import json
import re

SPORTYBET_API_BASE = "https://www.sportybet.com/api/ng"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://www.sportybet.com",
    "Referer": "https://www.sportybet.com/ng/",
    "operatingsystem": "pc",
    "clientid": "wap"
}


def clean_name(name):
    cleaned = re.sub(r'\b(FC|CF|SC|BC|KAA|FK|SK|VV|AIF|City|United)\b', '', name, flags=re.IGNORECASE).strip()
    return cleaned.split()[0] if cleaned else name


def search_live_event_id(team_name):
    """Finds live eventId on SportyBet."""
    keyword = clean_name(team_name)
    url = f"{SPORTYBET_API_BASE}/factsCenter/pcOrTabletsSearch"
    try:
        res = requests.get(url, params={"searchKey": keyword}, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            events = res.json().get("data", {}).get("events", [])
            for ev in events:
                if ev.get("status", 0) in [0, 1]:
                    return ev.get("eventId"), ev.get("homeTeamName"), ev.get("awayTeamName")
            if events:
                return events[0].get("eventId"), events[0].get("homeTeamName"), events[0].get("awayTeamName")
    except Exception:
        pass
    return None, None, None


def map_market_to_sportybet(market_pick):
    """
    Official SportyBet Market & Outcome IDs:
    - 1X2: marketId = 1 (Home = 1, Away = 3)
    - Double Chance: marketId = 10 (1X = 9, X2 = 11)
    - Draw No Bet: marketId = 14 (Home = 1, Away = 3)
    - Over/Under: marketId = 18 (Over = 12, Under = 13)
    """
    p = market_pick.lower()

    if "home win" in p:
        return {"marketId": "1", "outcomeId": "1", "specifier": None}
    if "away win" in p:
        return {"marketId": "1", "outcomeId": "3", "specifier": None}
    if "home or draw" in p or "1x" in p:
        return {"marketId": "10", "outcomeId": "9", "specifier": None}
    if "draw or away" in p or "x2" in p:
        return {"marketId": "10", "outcomeId": "11", "specifier": None}
    if "home dnb" in p:
        return {"marketId": "14", "outcomeId": "1", "specifier": None}
    if "away dnb" in p:
        return {"marketId": "14", "outcomeId": "3", "specifier": None}
    if "over 2.5" in p:
        return {"marketId": "18", "outcomeId": "12", "specifier": "total=2.5"}
    if "under 3.5" in p:
        return {"marketId": "18", "outcomeId": "13", "specifier": "total=3.5"}
    if "over 1.5" in p:
        return {"marketId": "18", "outcomeId": "12", "specifier": "total=1.5"}

    return {"marketId": "10", "outcomeId": "9", "specifier": None}


def generate_sportybet_code(legs):
    """
    Books the ticket directly to SportyBet's /orders/share API.
    """
    if not legs:
        return None, "No matches selected.", []

    sporty_outcomes = []
    booked_teams = []

    for leg in legs:
        event_id = leg.get("match_id", "")
        home_team = leg.get("home_team", "")
        away_team = leg.get("away_team", "")

        # If ID is not a direct SportyBet sr:match ID, search live board
        if not str(event_id).startswith("sr:match:"):
            found_id, h_live, a_live = search_live_event_id(home_team)
            if not found_id:
                found_id, h_live, a_live = search_live_event_id(away_team)
            if found_id:
                event_id = found_id
                home_team = h_live or home_team
                away_team = a_live or away_team

        if not str(event_id).startswith("sr:match:"):
            continue

        m_info = map_market_to_sportybet(leg.get("market_pick", ""))
        item = {
            "eventId": str(event_id),
            "marketId": m_info["marketId"],
            "outcomeId": m_info["outcomeId"]
        }
        if m_info["specifier"]:
            item["specifier"] = m_info["specifier"]

        sporty_outcomes.append(item)
        booked_teams.append(f"{home_team} vs {away_team} ({leg.get('market_pick')})")

    if not sporty_outcomes:
        return None, "Selected matches could not be matched with SportyBet's live IDs. Click 'Purge Stale Fixtures' in the sidebar to refresh.", []

    url = f"{SPORTYBET_API_BASE}/orders/share"
    try:
        res = requests.post(url, headers=HEADERS, json={"outcomes": sporty_outcomes}, timeout=8)
        if res.status_code == 200:
            data = res.json()
            code = data.get("data", {}).get("shareCode")
            if code:
                return str(code).upper(), None, booked_teams
            else:
                return None, data.get("message", "SportyBet rejected the selection parameters."), booked_teams
        elif res.status_code == 403:
            return None, "SportyBet rate limit. Wait 20 seconds and click again.", booked_teams
        else:
            return None, f"SportyBet server error HTTP {res.status_code}", booked_teams
    except Exception as e:
        return None, f"Network timeout: {str(e)}", booked_teams
