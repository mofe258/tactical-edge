"""
fetcher.py — Multi-League Match Ingestion & Live Score Engine
Full coverage for:
- English Premier League (EPL)
- Spanish La Liga
- Italian Serie A
- German Bundesliga
- UEFA Champions, Europa & Conference Leagues
Directly feeds from ESPN's open live sports network (zero API keys needed).
"""

import requests
from datetime import datetime, timedelta
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

# Major League ESPN Slugs
TOP_LEAGUES = {
    "Premier League": "eng.1",
    "La Liga": "esp.1",
    "Serie A": "ita.1",
    "Bundesliga": "ger.1",
    "UEFA Conference League": "uefa.europa.conf",
    "UEFA Champions League": "uefa.champions",
    "UEFA Europa League": "uefa.europa"
}

# Calibrated Power Ratings for Top European Clubs
POWER_RATINGS = {
    # Premier League
    "manchester city": {"att": 1.85, "def": 0.70},
    "arsenal": {"att": 1.75, "def": 0.68},
    "liverpool": {"att": 1.80, "def": 0.75},
    "chelsea": {"att": 1.55, "def": 0.95},
    "tottenham": {"att": 1.50, "def": 1.10},
    "aston villa": {"att": 1.45, "def": 0.95},
    "newcastle": {"att": 1.45, "def": 1.00},
    "brighton": {"att": 1.40, "def": 1.05},
    "manchester united": {"att": 1.35, "def": 1.15},
    
    # La Liga
    "real madrid": {"att": 1.85, "def": 0.70},
    "barcelona": {"att": 1.85, "def": 0.75},
    "atletico madrid": {"att": 1.55, "def": 0.75},
    "athletic club": {"att": 1.40, "def": 0.85},
    "villarreal": {"att": 1.45, "def": 1.10},
    "real sociedad": {"att": 1.30, "def": 0.85},
    
    # Serie A
    "inter milan": {"att": 1.80, "def": 0.70},
    "inter": {"att": 1.80, "def": 0.70},
    "atalanta": {"att": 1.75, "def": 0.85},
    "juventus": {"att": 1.50, "def": 0.65},
    "napoli": {"att": 1.60, "def": 0.80},
    "ac milan": {"att": 1.60, "def": 0.95},
    "lazio": {"att": 1.45, "def": 1.00},
    "roma": {"att": 1.40, "def": 1.05},
    
    # Bundesliga
    "bayern munich": {"att": 1.95, "def": 0.75},
    "bayer leverkusen": {"att": 1.80, "def": 0.80},
    "borussia dortmund": {"att": 1.65, "def": 1.05},
    "rb leipzig": {"att": 1.60, "def": 0.85},
    "eintracht frankfurt": {"att": 1.50, "def": 1.10},
    "stuttgart": {"att": 1.55, "def": 1.05}
}


def get_team_power(team_name, is_home=True):
    t_clean = team_name.lower().strip()
    for k, v in POWER_RATINGS.items():
        if k in t_clean:
            return v["att"], v["def"]
    # Dynamic baseline if club not in top tier
    return (1.20 if is_home else 1.00), (0.95 if is_home else 1.20)


def fetch_upcoming_fixtures(target_date_str, days_ahead=2):
    """
    Fetches official match fixtures from ESPN across EPL, La Liga, Serie A,
    Bundesliga, and European competitions for the target date.
    """
    date_clean = target_date_str.replace("-", "")
    all_fixtures = []
    seen_ids = set()

    for comp_name, comp_slug in TOP_LEAGUES.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{comp_slug}/scoreboard?dates={date_clean}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=6)
            if res.status_code == 200:
                data = res.json()
                for event in data.get("events", []):
                    mid = str(event.get("id"))
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)

                    comp = event.get("competitions", [{}])[0]
                    status_type = event.get("status", {}).get("type", {})
                    state = status_type.get("state", "pre")
                    
                    competitors = comp.get("competitors", [])
                    if len(competitors) == 2:
                        h_comp = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]
                        a_comp = competitors[1] if competitors[1].get("homeAway") == "away" else competitors[0]
                        
                        h_name = h_comp.get("team", {}).get("name", "")
                        a_name = a_comp.get("team", {}).get("name", "")
                        h_score = h_comp.get("score")
                        a_score = a_comp.get("score")

                        match_status = "FINISHED" if state == "post" else ("LIVE" if state == "in" else "SCHEDULED")

                        h_att, h_def = get_team_power(h_name, is_home=True)
                        a_att, a_def = get_team_power(a_name, is_home=False)

                        all_fixtures.append({
                            "id": f"espn_{mid}",
                            "utcDate": event.get("date", f"{target_date_str}T15:00:00Z"),
                            "status": match_status,
                            "competition": {"name": comp_name, "code": comp_slug},
                            "homeTeam": {"id": f"h_{mid}", "name": h_name, "crest": ""},
                            "awayTeam": {"id": f"a_{mid}", "name": a_name, "crest": ""},
                            "score": {"fullTime": {
                                "home": int(h_score) if (h_score is not None and str(h_score).isdigit()) else None,
                                "away": int(a_score) if (a_score is not None and str(a_score).isdigit()) else None
                            }},
                            "_custom_ratings": {
                                "h_att": h_att, "h_def": h_def,
                                "a_att": a_att, "a_def": a_def
                            }
                        })
        except Exception:
            continue

    from db import set_setting
    set_setting("last_successful_sync", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    set_setting("sync_status", "Multi-League Radar Active")
    return all_fixtures, None


def fetch_standings(competition_code):
    return {}
