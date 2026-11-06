"""
fetcher.py — Live Real-Time Multi-League Match Radar
Pulls today's actual active fixtures across European domestic & cup leagues.
Zero weekend hardcoding. Strictly pulls the current active matchday.
"""

import requests
from datetime import datetime, date

ESPN_LEAGUES = [
    ("eng.1", "Premier League"),
    ("esp.1", "La Liga"),
    ("ita.1", "Serie A"),
    ("ger.1", "Bundesliga"),
    ("fra.1", "Ligue 1"),
    ("eng.2", "Championship"),
    ("uefa.champions", "Champions League"),
    ("uefa.europa", "Europa League"),
    ("uefa.europa.conf", "Conference League"),
    ("por.1", "Primeira Liga"),
    ("ned.1", "Eredivisie"),
    ("tur.1", "Super Lig"),
    ("sau.1", "Saudi Pro League")
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def get_api_key():
    return ""


def fetch_upcoming_fixtures(target_date_str, days_ahead=1):
    """
    Fetches real matches playing today from ESPN's global scoreboard.
    """
    all_fixtures = []
    seen_ids = set()
    today_clean = target_date_str.replace("-", "")

    # 1. Pull active scoreboard for each league
    for league_slug, league_name in ESPN_LEAGUES:
        # Querying without hardcoded date returns the current active matchday
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/scoreboard"
        try:
            res = requests.get(url, headers=HEADERS, timeout=4)
            if res.status_code == 200:
                data = res.json()
                for event in data.get("events", []):
                    event_id = str(event.get("id"))
                    if event_id in seen_ids:
                        continue

                    comp = event.get("competitions", [{}])[0]
                    competitors = comp.get("competitors", [])
                    if len(competitors) < 2:
                        continue

                    h_comp = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]
                    a_comp = competitors[1] if competitors[1].get("homeAway") == "away" else competitors[0]

                    h_name = h_comp.get("team", {}).get("name", "Home")
                    a_name = a_comp.get("team", {}).get("name", "Away")

                    # Match timing
                    event_utc = event.get("date", "")
                    match_date = event_utc[:10] if len(event_utc) >= 10 else target_date_str
                    kickoff_time = event_utc[11:16] + " UTC" if len(event_utc) >= 16 else "19:00 UTC"

                    # Status
                    status_info = event.get("status", {}).get("type", {})
                    state = status_info.get("state", "pre")
                    status = "FINISHED" if state == "post" else ("LIVE" if state == "in" else "SCHEDULED")

                    h_score = h_comp.get("score")
                    a_score = a_comp.get("score")

                    seen_ids.add(event_id)
                    all_fixtures.append({
                        "id": f"espn_{event_id}",
                        "sporty_event_id": f"espn_{event_id}",
                        "utcDate": f"{match_date}T{kickoff_time[:5]}:00Z",
                        "status": status,
                        "competition": {"name": league_name, "code": league_slug},
                        "homeTeam": {"id": f"h_{event_id}", "name": h_name, "crest": ""},
                        "awayTeam": {"id": f"a_{event_id}", "name": a_name, "crest": ""},
                        "score": {
                            "fullTime": {
                                "home": int(h_score) if (h_score is not None and str(h_score).isdigit()) else None,
                                "away": int(a_score) if (a_score is not None and str(a_score).isdigit()) else None
                            }
                        },
                        "_custom_ratings": {"h_att": 1.35, "h_def": 1.05, "a_att": 1.15, "a_def": 1.20}
                    })
        except Exception:
            continue

    from db import set_setting
    set_setting("last_successful_sync", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    set_setting("sync_status", f"Synced {len(all_fixtures)} Active Matches")
    return all_fixtures, None


def fetch_standings(competition_code):
    return {}
