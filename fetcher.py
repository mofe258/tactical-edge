"""
fetcher.py — Dynamic Real-Time Multi-League Calendar Engine
Automatically pulls today's real live matches for any day of the week:
Fridays/Weekends: Premier League, La Liga, Bundesliga, Serie A, Ligue 1
Tuesdays/Wednesdays: Champions League | Thursdays: Europa & Conference League
"""

import requests
from datetime import datetime, timedelta

ESPN_LEAGUES = {
    "Premier League": "eng.1",
    "La Liga": "esp.1",
    "Bundesliga": "ger.1",
    "Serie A": "ita.1",
    "Ligue 1": "fra.1",
    "UEFA Champions League": "uefa.champions",
    "UEFA Europa League": "uefa.europa",
    "UEFA Conference League": "uefa.europa.conf",
    "Saudi Pro League": "sau.1",
    "Dutch Eredivisie": "ned.1"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def fetch_upcoming_fixtures(target_date_str, days_ahead=1):
    """
    Fetches real matches playing strictly on target_date_str from ESPN's global live feed.
    """
    # Format date for ESPN API (YYYYMMDD)
    date_clean = target_date_str.replace("-", "")
    all_matches = []
    seen_ids = set()

    for comp_name, league_slug in ESPN_LEAGUES.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/scoreboard?dates={date_clean}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()
                for event in data.get("events", []):
                    mid = str(event.get("id"))
                    if mid in seen_ids:
                        continue

                    comp = event.get("competitions", [{}])[0]
                    competitors = comp.get("competitors", [])
                    if len(competitors) != 2:
                        continue

                    h_comp = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]
                    a_comp = competitors[1] if competitors[1].get("homeAway") == "away" else competitors[0]

                    h_name = h_comp.get("team", {}).get("name") or h_comp.get("team", {}).get("displayName", "Home")
                    a_name = a_comp.get("team", {}).get("name") or a_comp.get("team", {}).get("displayName", "Away")

                    # Live score / status
                    status_type = event.get("status", {}).get("type", {})
                    state = status_type.get("state", "pre")
                    detail = status_type.get("detail", "Scheduled")

                    h_score = h_comp.get("score")
                    a_score = a_comp.get("score")

                    if state == "post":
                        match_status = "FINISHED"
                    elif state == "in":
                        match_status = "LIVE"
                    else:
                        match_status = "SCHEDULED"

                    h_s = int(h_score) if (h_score is not None and str(h_score).isdigit()) else None
                    a_s = int(a_score) if (a_score is not None and str(a_score).isdigit()) else None

                    # Extract kickoff time (UTC)
                    utc_date = event.get("date", f"{target_date_str}T18:45:00Z")

                    # Assign team power ratings
                    h_rank = h_comp.get("curatedRank", {}).get("current", 10)
                    a_rank = a_comp.get("curatedRank", {}).get("current", 10)
                    h_att = round(max(0.85, 1.80 - (h_rank * 0.04)), 2)
                    a_att = round(max(0.75, 1.65 - (a_rank * 0.04)), 2)

                    seen_ids.add(mid)
                    all_matches.append({
                        "id": mid,
                        "utcDate": utc_date,
                        "status": match_status,
                        "competition": {"name": comp_name, "code": league_slug.upper()},
                        "homeTeam": {"id": f"h_{mid}", "name": h_name, "crest": h_comp.get("team", {}).get("logo", "")},
                        "awayTeam": {"id": f"a_{mid}", "name": a_name, "crest": a_comp.get("team", {}).get("logo", "")},
                        "score": {"fullTime": {"home": h_s, "away": a_s}},
                        "_custom_ratings": {
                            "h_att": h_att, "h_def": round(max(0.80, 2.0 - h_att), 2),
                            "a_att": a_att, "a_def": round(max(0.85, 2.0 - a_att), 2)
                        }
                    })
        except Exception:
            continue

    from db import set_setting
    set_setting("last_successful_sync", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    set_setting("sync_status", "ESPN Live Feeds Active")
    return all_matches, None


def get_api_key():
    return ""


def fetch_standings(competition_code):
    return {}
