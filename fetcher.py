import requests

BASE_URL = "https://api.football-data.org/v4"

def fetch_daily_fixtures(api_key, match_date):
    """Fetches matches for the selected date with error handling."""
    headers = {"X-Auth-Token": api_key.strip()}
    url = f"{BASE_URL}/matches?dateFrom={match_date}&dateTo={match_date}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("matches", []), None
        elif res.status_code == 403:
            return [], "API Key Error: Invalid or inactive API key. (Wait 5-10 mins if just registered)."
        elif res.status_code == 429:
            return [], "Rate limit reached: Maximum 10 requests per minute on free tier."
        else:
            return [], f"API returned status code: {res.status_code}"
    except Exception as e:
        return [], f"Network error: {str(e)}"

def fetch_standings(api_key, competition_code):
    """Fetches league standings to calculate goal metrics."""
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
