import requests
from datetime import datetime, timedelta

BASE_URL = "https://api.football-data.org/v4"

def fetch_upcoming_fixtures(api_key, start_date_str, days_ahead=7):
    """
    Fetches matches across a multi-day window (default next 7 days)
    so you always have upcoming games to stake on.
    """
    headers = {"X-Auth-Token": api_key.strip()}
    
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = start_dt + timedelta(days=days_ahead)
    end_date_str = end_dt.strftime("%Y-%m-%d")

    url = f"{BASE_URL}/matches?dateFrom={start_date_str}&dateTo={end_date_str}"
    
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            return res.json().get("matches", []), None
        elif res.status_code == 403:
            return [], "API Key Error: Invalid or inactive API key."
        elif res.status_code == 429:
            return [], "Rate limit reached: Free plan allows 10 calls per minute."
        else:
            return [], f"API returned status code: {res.status_code}"
    except Exception as e:
        return [], f"Connection error: {str(e)}"

def fetch_standings(api_key, competition_code):
    """Fetches league standings to calculate attack and defense metrics."""
    headers = {"X-Auth-Token": api_key.strip()}
    url = f"{BASE_URL}/competitions/{competition_code}/standings"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            standings_data = res.json()
            team_stats = {}
            for table_group in standings_data.get("standings", []):
                if table_group.get("type") == "TOTAL":
                    for row in table_group.get("table", []):
                        team_name = row["team"]["name"]
                        played = max(1, row.get("playedGames", 1))
                        team_stats[team_name] = {
                            "att_strength": (row.get("goalsFor", 0) / played) / 1.35,
                            "def_strength": (row.get("goalsAgainst", 0) / played) / 1.35
                        }
            return team_stats
        return {}
    except Exception:
        return {}
