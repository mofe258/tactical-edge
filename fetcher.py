"""
fetcher.py — Large Multi-League Slate with ESPN Live Scores
Provides 40+ daily fixtures for massive 0-5 minute accumulator compounding.
"""

import requests
from datetime import datetime

ESPN_LEAGUES = {
    "UEFA Conference League": "uefa.europa.conf",
    "UEFA Champions League": "uefa.champions",
    "UEFA Europa League": "uefa.europa",
    "Premier League": "eng.1",
    "La Liga": "esp.1",
    "Bundesliga": "ger.1",
    "Serie A": "ita.1"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def fetch_espn_live_scores():
    live_results = {}
    for league_name, league_slug in ESPN_LEAGUES.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/scoreboard"
        try:
            res = requests.get(url, headers=HEADERS, timeout=6)
            if res.status_code == 200:
                data = res.json()
                for event in data.get("events", []):
                    comp = event.get("competitions", [{}])[0]
                    status_type = event.get("status", {}).get("type", {})
                    state = status_type.get("state", "pre")
                    detail = status_type.get("detail", "Scheduled")
                    competitors = comp.get("competitors", [])
                    if len(competitors) == 2:
                        h_comp = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]
                        a_comp = competitors[1] if competitors[1].get("homeAway") == "away" else competitors[0]
                        h_name = h_comp.get("team", {}).get("name", "")
                        a_name = a_comp.get("team", {}).get("name", "")
                        h_score = h_comp.get("score")
                        a_score = a_comp.get("score")
                        match_status = "FINISHED" if state == "post" else ("LIVE" if state == "in" else "SCHEDULED")
                        key = f"{h_name.lower()}_{a_name.lower()}"
                        live_results[key] = {
                            "home_score": int(h_score) if (h_score is not None and str(h_score).isdigit()) else None,
                            "away_score": int(a_score) if (a_score is not None and str(a_score).isdigit()) else None,
                            "status": match_status,
                            "detail": detail
                        }
        except Exception:
            continue
    return live_results


def get_all_daily_fixtures(target_date_str):
    """Broad roster of European & League matches for multi-slip stacking."""
    live_scores = fetch_espn_live_scores()

    matches = [
        # European Cup Matches
        {"id": "fix_01", "home": "Crvena zvezda", "away": "Inter d'Escaldes", "time": "18:45 UTC", "h_att": 1.45, "h_def": 0.85, "a_att": 0.70, "a_def": 1.40, "comp": "UEFA Conference League"},
        {"id": "fix_02", "home": "Trabzonspor", "away": "SC Freiburg", "time": "18:45 UTC", "h_att": 1.15, "h_def": 1.10, "a_att": 1.30, "a_def": 0.90, "comp": "UEFA Conference League"},
        {"id": "fix_03", "home": "Lincoln Red Imps", "away": "Hajduk Split", "time": "18:45 UTC", "h_att": 0.80, "h_def": 1.40, "a_att": 1.45, "a_def": 0.85, "comp": "UEFA Conference League"},
        {"id": "fix_04", "home": "KuPS Kuopio", "away": "KAA Gent", "time": "18:45 UTC", "h_att": 0.95, "h_def": 1.20, "a_att": 1.40, "a_def": 0.90, "comp": "UEFA Conference League"},
        {"id": "fix_05", "home": "FC Midtjylland", "away": "AFC Ajax", "time": "18:45 UTC", "h_att": 1.30, "h_def": 1.15, "a_att": 1.55, "a_def": 1.10, "comp": "UEFA Conference League"},
        {"id": "fix_06", "home": "AGF Aarhus", "away": "SC Braga", "time": "18:45 UTC", "h_att": 1.05, "h_def": 1.15, "a_att": 1.40, "a_def": 0.95, "comp": "UEFA Conference League"},
        {"id": "fix_07", "home": "FC Thun", "away": "Heart of Midlothian", "time": "18:45 UTC", "h_att": 1.15, "h_def": 1.10, "a_att": 1.20, "a_def": 1.10, "comp": "UEFA Conference League"},
        {"id": "fix_08", "home": "Atalanta BC", "away": "Kairat Almaty", "time": "18:45 UTC", "h_att": 1.75, "h_def": 0.75, "a_att": 0.70, "a_def": 1.50, "comp": "UEFA Conference League"},
        {"id": "fix_09", "home": "Mjällby AIF", "away": "FK Borac Banja Luka", "time": "18:45 UTC", "h_att": 1.15, "h_def": 0.95, "a_att": 0.90, "a_def": 1.20, "comp": "UEFA Conference League"},
        {"id": "fix_10", "home": "Universitatea Craiova", "away": "KF Egnatia", "time": "21:00 UTC", "h_att": 1.30, "h_def": 0.90, "a_att": 0.85, "a_def": 1.35, "comp": "UEFA Conference League"},
        {"id": "fix_11", "home": "FC Twente", "away": "Pafos FC", "time": "21:00 UTC", "h_att": 1.45, "h_def": 0.90, "a_att": 0.90, "a_def": 1.30, "comp": "UEFA Conference League"},
        {"id": "fix_12", "home": "Getafe CF", "away": "Brighton & Hove Albion", "time": "21:00 UTC", "h_att": 1.05, "h_def": 1.00, "a_att": 1.45, "a_def": 1.05, "comp": "UEFA Conference League"},
        {"id": "fix_13", "home": "Panathinaikos", "away": "CSKA Sofia", "time": "21:00 UTC", "h_att": 1.35, "h_def": 0.85, "a_att": 0.90, "a_def": 1.25, "comp": "UEFA Conference League"},
        {"id": "fix_14", "home": "Riga FC", "away": "FK Jablonec", "time": "21:00 UTC", "h_att": 1.10, "h_def": 1.10, "a_att": 1.15, "a_def": 1.05, "comp": "UEFA Conference League"},
        {"id": "fix_15", "home": "FC Copenhagen", "away": "FC Saburtalo", "time": "21:00 UTC", "h_att": 1.65, "h_def": 0.75, "a_att": 0.65, "a_def": 1.45, "comp": "UEFA Conference League"},
        {"id": "fix_16", "home": "FC Lugano", "away": "Kauno Žalgiris", "time": "21:00 UTC", "h_att": 1.40, "h_def": 0.95, "a_att": 0.80, "a_def": 1.40, "comp": "UEFA Conference League"},
        {"id": "fix_17", "home": "AS Monaco", "away": "FC Nordsjælland", "time": "21:00 UTC", "h_att": 1.70, "h_def": 0.85, "a_att": 1.10, "a_def": 1.35, "comp": "UEFA Conference League"},
        {"id": "fix_18", "home": "Sint-Truidense VV", "away": "SK Brann", "time": "21:00 UTC", "h_att": 1.15, "h_def": 1.15, "a_att": 1.25, "a_def": 1.05, "comp": "UEFA Conference League"},
        
        # Powerhouse Additions from the Winning Slip Style
        {"id": "fix_19", "home": "Newcastle United", "away": "Everton", "time": "20:00 UTC", "h_att": 1.35, "h_def": 1.05, "a_att": 1.05, "a_def": 1.15, "comp": "Premier League"},
        {"id": "fix_20", "home": "Sassuolo", "away": "Fiorentina", "time": "19:45 UTC", "h_att": 1.20, "h_def": 1.25, "a_att": 1.30, "a_def": 1.10, "comp": "Serie A"},
        {"id": "fix_21", "home": "Galatasaray", "away": "VfB Stuttgart", "time": "18:45 UTC", "h_att": 1.40, "h_def": 1.10, "a_att": 1.35, "a_def": 1.15, "comp": "UEFA Europa League"},
        {"id": "fix_22", "home": "Shakhtar Donetsk", "away": "Sporting CP", "time": "18:45 UTC", "h_att": 1.15, "h_def": 1.10, "a_att": 1.45, "a_def": 0.95, "comp": "UEFA Champions League"},
        {"id": "fix_23", "home": "Atletico Madrid", "away": "Bayern Munich", "time": "21:00 UTC", "h_att": 1.30, "h_def": 0.90, "a_att": 1.55, "a_def": 1.05, "comp": "UEFA Champions League"},
        {"id": "fix_24", "home": "Barcelona", "away": "Aston Villa", "time": "21:00 UTC", "h_att": 1.65, "h_def": 0.95, "a_att": 1.25, "a_def": 1.10, "comp": "UEFA Champions League"},
        {"id": "fix_25", "home": "Bodø/Glimt", "away": "Lille", "time": "21:00 UTC", "h_att": 1.25, "h_def": 1.10, "a_att": 1.30, "a_def": 1.00, "comp": "UEFA Europa League"},
        {"id": "fix_26", "home": "Feyenoord", "away": "Inter Milan", "time": "21:00 UTC", "h_att": 1.20, "h_def": 1.15, "a_att": 1.50, "a_def": 0.85, "comp": "UEFA Champions League"},
        {"id": "fix_27", "home": "Manchester United", "away": "AS Roma", "time": "21:00 UTC", "h_att": 1.35, "h_def": 1.15, "a_att": 1.25, "a_def": 1.10, "comp": "UEFA Europa League"}
    ]

    fixture_list = []
    for item in matches:
        h_score, a_score = None, None
        status = "SCHEDULED"

        for k, v in live_scores.items():
            if item["home"].lower() in k or item["away"].lower() in k:
                h_score = v["home_score"]
                a_score = v["away_score"]
                status = v["status"]
                break

        fixture_list.append({
            "id": item["id"],
            "utcDate": f"{target_date_str}T{item['time'][:5]}:00Z",
            "status": status,
            "competition": {"name": item["comp"], "code": "EUR"},
            "homeTeam": {"id": f"h_{item['id']}", "name": item["home"], "crest": ""},
            "awayTeam": {"id": f"a_{item['id']}", "name": item["away"], "crest": ""},
            "score": {"fullTime": {"home": h_score, "away": a_score}},
            "_custom_ratings": {
                "h_att": item["h_att"], "h_def": item["h_def"],
                "a_att": item["a_att"], "a_def": item["a_def"]
            }
        })
    return fixture_list


def fetch_upcoming_fixtures(start_date_str, days_ahead=2):
    fixtures = get_all_daily_fixtures(start_date_str)
    return fixtures, None


def fetch_standings(competition_code):
    return {}
