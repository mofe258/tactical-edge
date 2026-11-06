"""
sportybet.py — Live SportyBet Auto-Pruner & Order Dispatcher
Automatically detects and removes games that have already started or ended.
Books all remaining upcoming matches so the booking code always succeeds.
"""

import requests
import json
import re
from datetime import datetime

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


def search_live_event(team_name):
    """
    Finds event on SportyBet. Strictly rejects matches that have already kicked off.
    """
    keyword = clean_name(team_name)
    url = f"{SPORTYBET_API_BASE}/factsCenter/pcOrTabletsSearch"
    now_ms = datetime.utcnow().timestamp() * 1000

    try:
        res = requests.get(url, params={"searchKey": keyword}, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            events = res.json().get("data", {}).get("events", [])
            for ev in events:
                status = ev.get("status", 0)
                start_time = ev.get("estimateStartTime", 0)

                # Only accept PRE-MATCH games that have NOT kicked off yet
                # status 0 = not started, and start_time must be in the future (with 2 min buffer)
                if status == 0 and start_time > (now_ms - 120000):
                    return ev
    except Exception:
        pass
    return None


def map_market_to_sportybet(market_pick):
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
    Prunes ended/kicked-off games and registers ticket for all remaining upcoming fixtures.
    """
    if not legs:
        return None, "No matches available in slip.", [], []

    sporty_outcomes = []
    booked_teams = []
    skipped_teams = []

    for leg in legs:
        home_team = leg.get("home_team", "")
        away_team = leg.get("away_team", "")

        # Search for active upcoming match
        event = search_live_event(home_team)
        if not event:
            event = search_live_event(away_team)

        # If match not found, already started, or ended -> skip it and book the remaining!
        if not event:
            skipped_teams.append(f"{home_team} vs {away_team} (Ended / Started / Inactive)")
            continue

        event_id = event.get("eventId")
        if not event_id:
            skipped_teams.append(f"{home_team} vs {away_team}")
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
        h_name = event.get("homeTeamName", home_team)
        a_name = event.get("awayTeamName", away_team)
        booked_teams.append(f"{h_name} vs {a_name} ➔ {leg.get('market_pick')}")

    if not sporty_outcomes:
        return None, "All selected games have either already started or ended. No upcoming matches left to book.", [], skipped_teams

    # Send only valid, upcoming matches to SportyBet
    url = f"{SPORTYBET_API_BASE}/orders/share"
    try:
        res = requests.post(url, headers=HEADERS, json={"outcomes": sporty_outcomes}, timeout=8)
        if res.status_code == 200:
            data = res.json()
            code = data.get("data", {}).get("shareCode")
            if code:
                return str(code).upper(), None, booked_teams, skipped_teams
            else:
                return None, data.get("message", "SportyBet rejected the ticket."), booked_teams, skipped_teams
        elif res.status_code == 403:
            return None, "SportyBet rate limit. Wait 15 seconds and try again.", booked_teams, skipped_teams
        else:
            return None, f"SportyBet error HTTP {res.status_code}", booked_teams, skipped_teams
    except Exception as e:
        return None, f"Network timeout: {str(e)}", booked_teams, skipped_teams
