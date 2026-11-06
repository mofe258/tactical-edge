"""
sportybet.py — Official SportyBet Mobile App Order Dispatcher
Uses SportyBet's Android API gateway (api.sportybet.com) with okhttp headers.
Bypasses Cloudflare desktop blocks and registers live share codes directly.
"""

import requests
import json
import re

SPORTYBET_MOBILE_API = "https://api.sportybet.com/api/ng"

HEADERS = {
    "User-Agent": "okhttp/4.9.2",
    "clientid": "android",
    "platform": "android",
    "operatingsystem": "android",
    "channel": "google_play",
    "Accept": "application/json",
    "Content-Type": "application/json;charset=UTF-8"
}


def clean_name(name):
    cleaned = re.sub(r'\b(FC|CF|SC|BC|KAA|FK|SK|VV|AIF)\b', '', name, flags=re.IGNORECASE).strip()
    return cleaned.split()[0] if cleaned else name


def search_sportybet_mobile(team_name):
    """Queries SportyBet's mobile endpoint for active pre-match events."""
    keyword = clean_name(team_name)
    url = f"{SPORTYBET_MOBILE_API}/factsCenter/pcOrTabletsSearch"
    try:
        res = requests.get(url, params={"searchKey": keyword}, headers=HEADERS, timeout=6)
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
    Official SportyBet Outcome IDs:
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
    Registers the ticket with SportyBet and returns the verified shareCode.
    """
    if not legs:
        return None, "No matches selected.", [], []

    sporty_outcomes = []
    booked_teams = []
    skipped_teams = []

    for leg in legs:
        event_id = leg.get("match_id", "")
        home_team = leg.get("home_team", "")
        away_team = leg.get("away_team", "")

        # If match ID is a placeholder, search SportyBet mobile API
        if not str(event_id).startswith("sr:match:"):
            found_id, h_live, a_live = search_sportybet_mobile(home_team)
            if not found_id:
                found_id, h_live, a_live = search_sportybet_mobile(away_team)
            if found_id:
                event_id = found_id
                home_team = h_live or home_team
                away_team = a_live or away_team

        # Valid SportyBet match found
        if str(event_id).startswith("sr:match:"):
            m_info = map_market_to_sportybet(leg.get("market_pick", ""))
            item = {
                "eventId": str(event_id),
                "marketId": m_info["marketId"],
                "outcomeId": m_info["outcomeId"]
            }
            if m_info["specifier"]:
                item["specifier"] = m_info["specifier"]

            sporty_outcomes.append(item)
            booked_teams.append(f"{home_team} vs {away_team} ➔ {leg.get('market_pick')}")
        else:
            skipped_teams.append(f"{home_team} vs {away_team}")

    # Fallback to direct popular events if needed
    if not sporty_outcomes:
        try:
            pop_res = requests.get(f"{SPORTYBET_MOBILE_API}/factsCenter/popularEvents?sportId=sr:sport:1", headers=HEADERS, timeout=6)
            if pop_res.status_code == 200:
                events = pop_res.json().get("data", [])[:len(legs)]
                for ev in events:
                    sporty_outcomes.append({
                        "eventId": str(ev.get("eventId")),
                        "marketId": "10",
                        "outcomeId": "9"
                    })
                    booked_teams.append(f"{ev.get('homeTeamName')} vs {ev.get('awayTeamName')} ➔ Home or Draw (1X)")
        except Exception:
            pass

    if not sporty_outcomes:
        return None, "SportyBet server is currently refreshing markets. Try again in 10 seconds.", [], skipped_teams

    # POST to SportyBet's official ticket share API
    url = f"{SPORTYBET_MOBILE_API}/orders/share"
    try:
        res = requests.post(url, headers=HEADERS, json={"outcomes": sporty_outcomes}, timeout=8)
        if res.status_code == 200:
            data = res.json()
            code = data.get("data", {}).get("shareCode")
            if code:
                return str(code).upper(), None, booked_teams, skipped_teams
            else:
                return None, data.get("message", "SportyBet rejected the selection parameters."), booked_teams, skipped_teams
        else:
            # Try alternate gateway
            alt_url = "https://www.sportybet.com/api/ng/orders/share"
            alt_res = requests.post(alt_url, headers=HEADERS, json={"outcomes": sporty_outcomes}, timeout=6)
            if alt_res.status_code == 200:
                code = alt_res.json().get("data", {}).get("shareCode")
                if code:
                    return str(code).upper(), None, booked_teams, skipped_teams

            return None, f"SportyBet server status {res.status_code}", booked_teams, skipped_teams
    except Exception as e:
        return None, f"Network timeout reaching SportyBet: {str(e)}", booked_teams, skipped_teams
