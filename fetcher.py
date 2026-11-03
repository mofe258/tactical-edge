"""
fetcher.py — Football-Data.org API Client & Data Provider Attribution
Pulls official schedules, live scores, standings, and team crest URLs.
"""

import os
import requests
from datetime import datetime, timedelta
import streamlit as st

BASE_URL = "https://api.football-data.org/v4"


def get_api_key():
    try:
        if hasattr(st, "secrets") and "FOOTBALL_API_KEY" in st.secrets:
            key = str(st.secrets["FOOTBALL_API_KEY"]).strip()
            if key and key != "PASTE_YOUR_API_KEY_HERE":
                return key
    except Exception:
        pass

    env_key = os.getenv("FOOTBALL_API_KEY", "").strip()
    if env_key:
        return env_key

    try:
        from db import get_setting
        db_key = get_setting("FOOTBALL_API_KEY", "").strip()
        if db_key and db_key != "PASTE_YOUR_API_KEY_HERE":
            return db_key
    except Exception:
        pass

    return ""


@st.cache_data(ttl=600, show_spinner=False)
def fetch_upcoming_fixtures(start_date_str, days_ahead=7):
    """
    Fetches official match schedules, live statuses, and verified team crests.
    """
    api_key = get_api_key()
    if not api_key:
        return [], "API Key Missing. Add FOOTBALL_API_KEY in sidebar or Streamlit secrets."

    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=days_ahead)
        end_date_str = end_dt.strftime("%Y-%m-%d")
    except Exception as e:
        return [], f"Date parsing error: {e}"

    headers = {"X-Auth-Token": api_key}
    url = f"{BASE_URL}/matches?dateFrom={start_date_str}&dateTo={end_date_str}"

    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            matches = res.json().get("matches", [])
            # Store timestamp for Data Freshness Indicator
            from db import set_setting
            set_setting("last_successful_sync", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
            return matches, None
        elif res.status_code == 403:
            return [], "Authentication Error (403): Invalid API key on football-data.org."
        elif res.status_code == 429:
            return [], "Rate limit reached (429): Maximum 10 requests per minute on free tier."
        else:
            return [], f"API returned status code: {res.status_code}"
    except Exception as e:
        return [], f"Connection error: {str(e)}"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_standings(competition_code):
    """Fetches full league standings table in one request."""
    api_key = get_api_key()
    if not api_key:
        return {}

    headers = {"X-Auth-Token": api_key}
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
                        gf = row.get("goalsFor", 0)
                        ga = row.get("goalsAgainst", 0)

                        team_stats[team_name] = {
                            "att_strength": round((gf / played) / 1.35, 3),
                            "def_strength": round((ga / played) / 1.35, 3),
                            "played": played,
                            "gf": gf,
                            "ga": ga,
                            "form": row.get("form", "N/A"),
                            "points": row.get("points", 0),
                            "position": row.get("position", 0),
                            "crest": row["team"].get("crest", "")
                        }
            return team_stats
        return {}
    except Exception:
        return {}
