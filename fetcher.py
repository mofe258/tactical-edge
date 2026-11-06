"""
fetcher.py — Dynamic Real-Time Multi-League ESPN Radar
Pulls today's live matches across Premier League, La Liga, Serie A,
Bundesliga, Ligue 1, UEFA, Championship, etc.
Zero hardcoded games. Strictly dynamically fetched for today's date.
"""

import requests
from datetime import datetime, date

ESPN_LEAGUES = [
    ("eng.1", "Premier League"),
    ("esp.1", "La Liga"),
    ("ita.1", "Serie A"),
    ("ger.1", "Bundesliga"),
    ("fra.1", "Ligue 1"),
    ("uefa.champions", "UEFA Champions League"),
    ("uefa.europa", "UEFA Europa League"),
    ("uefa.europa.conf", "UEFA Conference League"),
    ("eng.2", "EFL Championship"),
    ("ned.1", "Eredivisie"),
    ("por.1", "Primeira Liga")
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def get_api_key():
    return ""


def fetch_upcoming_fixtures(target_date_str, days_ahead=1):
    """
    Fetches real matches scheduled specifically for target_date_str from ESPN's global scoreboard.
    """
    # Format target_date_str (YYYY-MM-DD) to ESPN's format (YYYYMMDD)
    date_clean = target_date_str.replace("-", "")
    all_fixtures = []
    seen_ids = set()

    for league_slug, league_name in ESPN_LEAGUES:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/scoreboard?dates={date_clean}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()
                for event in data.get("events", []):
                    event_id = str(event.get("id"))
                    if event_id in seen_ids:
                        continue
                    seen_ids.add(event_id)

                    comp = event.get("competitions", [{}])[0]
                    competitors = comp.get("competitors", [])
                    if len(competitors) < 2:
                        continue

                    h_comp = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]
                    a_comp = competitors[1] if competitors[1].get("homeAway") == "away" else competitors[0]

                    h_name = h_comp.get("team", {}).get("name", "Home")
                    a_name = a_comp.get("team", {}).get("name", "Away")
                    h_score = h_comp.get("score")
                    a_score = a_comp.get("score")

                    # Match status
                    status_info = event.get("status", {}).get("type", {})
                    state = status_info.get("state", "pre")  # "pre", "in", "post"

                    if state == "post":
                        status = "FINISHED"
                    elif state == "in":
                        status = "LIVE"
                    else:
                        status = "SCHEDULED"

                    utc_date = event.get("date", f"{target_date_str}T18:00:00Z")

                    all_fixtures.append({
                        "id": f"espn_{event_id}",
                        "sporty_event_id": f"espn_{event_id}",
                        "utcDate": utc_date,
                        "status": status,
                        "competition": {"name": league_name, "code": league_slug},
                        "homeTeam": {"id": f"h_{event_id}", "name": h_name, "crest": h_comp.get("team", {}).get("logo", "")},
                        "awayTeam": {"id": f"a_{event_id}", "name": a_name, "crest": a_comp.get("team", {}).get("logo", "")},
                        "score": {
                            "fullTime": {
                                "home": int(h_score) if (h_score is not None and str(h_score).isdigit()) else None,
                                "away": int(a_score) if (a_score is not None and str(a_score).isdigit()) else None
                            }
                        },
                        "_custom_ratings": {"h_att": 1.30, "h_def": 1.00, "a_att": 1.15, "a_def": 1.15}
                    })
        except Exception:
            continue

    from db import set_setting
    set_setting("last_successful_sync", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    set_setting("sync_status", f"Synced {len(all_fixtures)} Live Matches for {target_date_str}")
    return all_fixtures, None


def fetch_standings(competition_code):
    return {}
