"""
sportybet.py — Official SportyBet Server Order Client (Nigeria)
Connects directly to SportyBet's /orders/share API.
Zero fake codes. Only authentic server-issued share codes.
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


def clean_team_name(name):
    """Strips club initials to ensure SportyBet's search engine finds the match."""
    # Remove common club abbreviations
    cleaned = re.sub(r'\b(FC|CF|SC|BC|KAA|FK|SK|VV|AIF|Kuopio|Almaty|Banja Luka|Midlothian)\b', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Take the primary distinct team identifier
    parts = cleaned.split()
    return parts[0] if parts else name


def search_sportybet_event(team_name):
    """Queries SportyBet's database for the live event ID."""
    search_keyword = clean_team_name(team_name)
    url = f"{SPORTYBET_API_BASE}/factsCenter/pcOrTabletsSearch"
    params = {"searchKey": search_keyword}

    try:
        res = requests.get(url, params=params, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            events = res.json().get("data", {}).get("events", [])
            for ev in events:
                # Match sport soccer
                if ev.get("sport", {}).get("id") == "sr:sport:1" or "sportId" in str(ev):
                    return ev
            if events:
                return events[0]
    except Exception:
        pass
    return None


def map_market_to_sportybet(market_pick):
    """
    Official SportyBet Market & Outcome IDs:
    - 1X2: marketId = 1 (Home = 1, Draw = 2, Away = 3)
    - Double Chance: marketId = 10 (1X = 9, 12 = 10, X2 = 11)
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

    # Default to Double Chance 1X
    return {"marketId": "10", "outcomeId": "9", "specifier": None}


def generate_sportybet_code(legs):
    """
    Contacts SportyBet's /orders/share API.
    Returns: (code, error_message, booked_matches_list)
    """
    if not legs:
        return None, "No matches selected to book.", []

    sporty_outcomes = []
    booked_teams = []

    for leg in legs:
        home_team = leg.get("home_team", "")
        event = search_sportybet_event(home_team)
        if not event:
            continue

        event_id = event.get("eventId")
        if not event_id:
            continue

        m_info = map_market_to_sportybet(leg.get("market_pick", ""))

        item = {
            "eventId": event_id,
            "marketId": m_info["marketId"],
            "outcomeId": m_info["outcomeId"]
        }
        if m_info["specifier"]:
            item["specifier"] = m_info["specifier"]

        sporty_outcomes.append(item)
        booked_teams.append(f"{event.get('homeTeamName', home_team)} vs {event.get('awayTeamName', leg.get('away_team'))} ({leg.get('market_pick')})")

    if not sporty_outcomes:
        return None, "Could not match selected fixtures on SportyBet's live schedule. Matches may have already kicked off or markets are closed.", []

    # Send order to SportyBet's official ticket sharing API
    url = f"{SPORTYBET_API_BASE}/orders/share"
    try:
        res = requests.post(url, headers=HEADERS, json={"outcomes": sporty_outcomes}, timeout=8)
        if res.status_code == 200:
            data = res.json()
            code = data.get("data", {}).get("shareCode")
            if code:
                return str(code).upper(), None, booked_teams
            else:
                msg = data.get("message", "SportyBet rejected selection parameters.")
                return None, f"SportyBet server error: {msg}", booked_teams
        elif res.status_code == 403:
            return None, "SportyBet Cloudflare rate limit: Try again in 30 seconds.", booked_teams
        else:
            return None, f"SportyBet server HTTP {res.status_code}", booked_teams
    except Exception as e:
        return None, f"Network timeout reaching SportyBet: {str(e)}", booked_teams
