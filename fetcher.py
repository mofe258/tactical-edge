"""
fetcher.py — Team-Specific Tactical Profiler for Queen Rins
Profiles teams individually so defensive clubs (KuPS, Lincoln, Mjallby)
never share identical offensive ratings with heavyweights (Ajax, Bayern).
"""

import requests
from datetime import datetime, date

# Specific Tactical Profiles: [Attack Rating, Defense Rating]
TEAM_PROFILES = {
    # High-Scoring Offenses
    "ajax": (1.65, 1.15),
    "bayern": (1.90, 0.90),
    "manchester city": (1.85, 0.85),
    "arsenal": (1.70, 0.80),
    "liverpool": (1.75, 0.85),
    "barcelona": (1.80, 0.85),
    "real madrid": (1.80, 0.80),
    "psg": (1.80, 0.85),
    "monaco": (1.65, 0.95),
    "copenhagen": (1.55, 0.80),
    "atalanta": (1.70, 0.80),

    # Defensive / Low-Scoring Teams (Under 3.5 Specialists)
    "kups": (0.85, 0.95),
    "gent": (1.25, 0.85),
    "lincoln": (0.75, 1.10),
    "hajduk": (1.20, 0.85),
    "mjällby": (1.10, 0.75),
    "mjallby": (1.10, 0.75),
    "borac": (0.80, 1.05),
    "hearts": (1.05, 1.05),
    "thun": (1.15, 1.10),
    "freiburg": (1.15, 0.90),
    "trabzonspor": (1.10, 1.05),
    "aarhus": (0.95, 1.05),
    "braga": (1.30, 0.90),
    "zalgiris": (0.85, 1.15),
    "lugano": (1.25, 0.95),
    "twente": (1.35, 0.90),
    "pafos": (0.90, 1.10)
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def get_team_profile(team_name, is_home=True):
    name_clean = team_name.lower()
    for key, profile in TEAM_PROFILES.items():
        if key in name_clean:
            return profile[0], profile[1]
    # Realistic default if club not explicitly profiled
    return (1.20, 1.00) if is_home else (1.00, 1.15)


def fetch_upcoming_fixtures(target_date_str, days_ahead=1):
    """
    Pulls live match scoreboard and applies team-specific tactical ratings.
    """
    all_fixtures = []
    seen_ids = set()

    leagues = [
        ("uefa.europa.conf", "Conference League"),
        ("uefa.europa", "Europa League"),
        ("uefa.champions", "Champions League"),
        ("eng.1", "Premier League"),
        ("esp.1", "La Liga"),
        ("ita.1", "Serie A"),
        ("ger.1", "Bundesliga"),
        ("fra.1", "Ligue 1")
    ]

    for league_slug, league_name in leagues:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/scoreboard"
        try:
            res = requests.get(url, headers=HEADERS, timeout=4)
            if res.status_code == 200:
                for event in res.json().get("events", []):
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

                    # Look up individual team profiles
                    h_att, h_def = get_team_profile(h_name, is_home=True)
                    a_att, a_def = get_team_profile(a_name, is_home=False)

                    event_utc = event.get("date", "")
                    match_date = event_utc[:10] if len(event_utc) >= 10 else target_date_str
                    kickoff_time = event_utc[11:16] + " UTC" if len(event_utc) >= 16 else "18:45 UTC"

                    status_info = event.get("status", {}).get("type", {})
                    state = status_info.get("state", "pre")
                    status = "FINISHED" if state == "post" else ("LIVE" if state == "in" else "SCHEDULED")

                    h_score = h_comp.get("score")
                    a_score = a_comp.get("score")

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
                        "_custom_ratings": {"h_att": h_att, "h_def": h_def, "a_att": a_att, "a_def": a_def}
                    })
        except Exception:
            continue

    from db import set_setting
    set_setting("last_successful_sync", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    set_setting("sync_status", f"Synced {len(all_fixtures)} Profiled Matches")
    return all_fixtures, None


def fetch_standings(competition_code):
    return {}
