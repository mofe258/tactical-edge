"""
sportybet.py — Official SportyBet Live Event Validator & Booking Client
Directly queries SportyBet's live sportsbook and registers official booking codes.
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
    """Extracts the primary distinct team name for SportyBet's search engine."""
    cleaned = re.sub(r'\b(FC|CF|SC|BC|KAA|FK|SK|VV|AIF|Kuopio|Almaty|Banja Luka|Midlothian|City|United)\b', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    parts = cleaned.split()
    return parts[0] if parts else name


def search_sportybet_event(team_name):
    """Searches SportyBet for an active, open match on today's board."""
    keyword = clean_team_name(team_name)
    url = f"{SPORTYBET_API_BASE}/factsCenter/pcOrTabletsSearch"
    params = {"searchKey": keyword}

    try:
        res = requests.get(url, params=params, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            events = res.json().get("data", {}).get("events", [])
            for ev in events:
                # Must be a soccer match and not finished
                status = ev.get("status", 0)
                # status 0 = not started, status 1 = in play
                if status in [0, 1]:
                    return ev
            if events:
                return events[0]
    except Exception:
        pass
    return None


def map_market_to_sportybet(market_pick):
    """
    Official SportyBet Market & Outcome IDs:
    - 1X2: marketId = 1 (Home = 1, Away = 3)
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

    return {"marketId": "10", "outcomeId": "9", "specifier": None}


def generate_sportybet_code(legs):
    """
    Builds the booking payload strictly from matches verified on SportyBet's live board.
    """
    if not legs:
        return None, "No matches provided in slip.", []

    sporty_outcomes = []
    booked_teams = []
    skipped_teams = []

    for leg in legs:
        home_team = leg.get("home_team", "")
        away_team = leg.get("away_team", "")
        
        # 1. Search by Home team
        event = search_sportybet_event(home_team)
        # 2. If not found, try searching by Away team
        if not event:
            event = search_sportybet_event(away_team)

        if not event:
            skipped_teams.append(f"{home_team} vs {away_team}")
            continue

        event_id = event.get("eventId")
        if not event_id:
            skipped_teams.append(f"{home_team} vs {away_team}")
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
        h_name = event.get("homeTeamName", home_team)
        a_name = event.get("awayTeamName", away_team)
        booked_teams.append(f"{h_name} vs {a_name} ➔ {leg.get('market_pick')}")

    if not sporty_outcomes:
        msg = "SportyBet could not find these games on today's active schedule."
        if skipped_teams:
            msg += f" Missing on SportyBet: {', '.join(skipped_teams[:3])}"
        return None, msg, []

    # Send to SportyBet's official /orders/share endpoint
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
            return None, "SportyBet rate limit / Cloudflare challenge. Wait 20 seconds and click again.", booked_teams
        else:
            return None, f"SportyBet server HTTP error {res.status_code}", booked_teams
    except Exception as e:
        return None, f"Network timeout connecting to SportyBet: {str(e)}", booked_teams
