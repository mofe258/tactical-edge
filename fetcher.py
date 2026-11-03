"""
fetcher.py — Football-Data.org API Client & Data Synchronization Layer
Fetches official match schedules, live scores, standings, team crests,
and tracks synchronization timestamps.
"""

import os
import requests
from datetime import datetime, timedelta
import streamlit as st

BASE_URL = "https://api.football-data.org/v4"


def get_api_key():
    """Extracts API key from Streamlit secrets, environment variables, or SQLite."""
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


@st.cache_data(ttl=300, show_spinner=False)
def fetch_upcoming_fixtures(start_date_str, days_ahead=7):
    """
    Queries matches across the scheduled date window.
    Caches for 5 minutes to remain strictly within the 10 calls/min rate limit.
    """
    api_key = get_api_key()
    if not api_key:
        from db import set_setting
        set_setting("sync_status", "Awaiting Initial Sync")
        return [], "API Key Missing. Add FOOTBALL_API_KEY in the sidebar or Streamlit secrets."

    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=days_ahead)
        end_date_str = end_dt.strftime("%Y-%m-%d")
    except Exception as e:
        return [], f"Date parsing error: {e}"

    headers = {"X-Auth-Token": api_key}
    url = f"{BASE_URL}/matches?dateFrom={start_date_str}&dateTo={end_date_str}"

    from db import set_setting
    try:
        res = requests.get(url, headers=headers, timeout=12)
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        if res.status_code == 200:
            matches = res.json().get("matches", [])
            set_setting("last_successful_sync", now_str)
            set_setting("sync_status", "Live / Updated")
            return matches, None
        elif res.status_code == 403:
            set_setting("last_failed_sync", now_str)
            set_setting("sync_status", "Failed (Invalid API Key)")
            return [], "Authentication Error (403): Invalid API key on football-data.org."
        elif res.status_code == 429:
            set_setting("sync_status", "Delayed (Rate Limit)")
            return [], "Rate limit reached (429): Maximum 10 requests per minute on free tier."
        else:
            set_setting("last_failed_sync", now_str)
            set_setting("sync_status", f"Failed (Code {res.status_code})")
            return [], f"API returned status code: {res.status_code}"
    except requests.exceptions.Timeout:
        set_setting("sync_status", "Failed (Timeout)")
        return [], "Connection timeout: football-data.org did not respond within 12 seconds."
    except Exception as e:
        set_setting("sync_status", "Failed (Network Error)")
        return [], f"Network error: {str(e)}"


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_standings(competition_code):
    """
    Retrieves full standings for a competition. Indexes by both official team ID
    and normalized team names to prevent fallback defaults.
    """
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
                        team_id = str(row["team"]["id"])
                        team_name = row["team"]["name"].strip()
                        played = max(1, row.get("playedGames", 1))
                        gf = row.get("goalsFor", 0)
                        ga = row.get("goalsAgainst", 0)

                        stat_entry = {
                            "att_strength": round((gf / played) / 1.35, 3),
                            "def_strength": round((ga / played) / 1.35, 3),
                            "played": played,
                            "gf": gf,
                            "ga": ga,
                            "gf_per_game": round(gf / played, 2),
                            "ga_per_game": round(ga / played, 2),
                            "form": row.get("form", "N/A"),
                            "points": row.get("points", 0),
                            "position": row.get("position", 0),
                            "crest": row["team"].get("crest", "")
                        }
                        # Index by both ID and Name to ensure matches always find team-specific stats
                        team_stats[team_id] = stat_entry
                        team_stats[team_name] = stat_entry
                        team_stats[team_name.lower()] = stat_entry
            return team_stats
        return {}
    except Exception:
        return {}
