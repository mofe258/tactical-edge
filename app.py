import streamlit as st
import pandas as pd
from datetime import date
import db
from engine import FootballEngine
import fetcher

st.set_page_config(page_title="Tactical Edge Predictor", layout="wide", page_icon="⚽")
db.init_db()

st.title("⚽ Tactical Edge - Algorithmic Selections")
st.markdown("Picks are locked and mathematically computed from live team performance metrics.")

with st.sidebar:
    st.header("⚙️ Configuration")
    
    api_key_default = ""
    try:
        if hasattr(st, "secrets") and "FOOTBALL_API_KEY" in st.secrets:
            api_key_default = st.secrets["FOOTBALL_API_KEY"]
    except Exception:
        pass

    api_key = st.text_input("football-data.org API Key", value=api_key_default, type="password")
    min_confidence = st.slider("Min Probability Filter (%)", min_value=60, max_value=85, value=70, step=1) / 100.0
    
    st.divider()
    scan_days = st.selectbox("Scan Horizon", [3, 5, 7], index=2, format_func=lambda x: f"Next {x} Days")
    start_date = st.date_input("From Date", value=date.today()).strftime("%Y-%m-%d")
    
    if st.button("🚀 Fetch Upcoming Matches"):
        if not api_key:
            st.error("Please enter your API Key!")
        else:
            with st.spinner(f"Scanning the next {scan_days} days for fixtures and stats..."):
                fixtures, err_msg = fetcher.fetch_upcoming_fixtures(api_key, start_date, days_ahead=scan_days)
                
                if err_msg:
                    st.error(err_msg)
                elif not fixtures:
                    st.warning(f"No matches scheduled across free-tier leagues in the next {scan_days} days.")
                else:
                    engine = FootballEngine()
                    standings_cache = {}
                    count = 0

                    for m in fixtures:
                        comp_code = m.get("competition", {}).get("code")
                        if not comp_code:
                            continue
                        
                        match_date = m.get("utcDate", "")[:10]
                        
                        if comp_code not in standings_cache:
                            standings_cache[comp_code] = fetcher.fetch_standings(api_key, comp_code)
                            
                        team_stats = standings_cache[comp_code]
                        h_team = m["homeTeam"]["name"]
                        a_team = m["awayTeam"]["name"]
                        
                        h_stat = team_stats.get(h_team, {"att_strength": 1.0, "def_strength": 1.0})
                        a_stat = team_stats.get(a_team, {"att_strength": 1.0, "def_strength": 1.0})
                        
                        h_xg, a_xg = engine.calculate_xg(
                            h_stat["att_strength"], h_stat["def_strength"],
                            a_stat["att_strength"], a_stat["def_strength"]
                        )
                        probs = engine.predict_match(h_xg, a_xg)
                        
                        safest_market = max(probs, key=probs.get)
                        safest_prob = probs[safest_market]

                        if safest_prob >= min_confidence:
                            db.save_prediction(
                                match_date, 
                                str(m["id"]), 
                                m["competition"]["name"],
                                h_team, 
                                a_team, 
                                safest_market, 
                                safest_prob
                            )
                            count += 1
                    
                    if count > 0:
                        st.success(f"Success! Analyzed schedule and locked {count} high-confidence picks.")
                        st.rerun()
                    else:
                        st.info("Fixtures were found, but none met your minimum probability threshold. Try lowering the slider to 65%.")

# Main Display: Shows all locked upcoming picks
st.subheader("📋 Locked Value Board")

# Query all locked predictions from SQLite
import sqlite3
conn = sqlite3.connect(db.DB_NAME)
c = conn.cursor()
c.execute("SELECT match_date, competition, home_team, away_team, market, confidence, locked_at FROM predictions ORDER BY match_date ASC")
raw_data = c.fetchall()
conn.close()

if raw_data:
    df = pd.DataFrame(raw_data, columns=["Match Date", "Competition", "Home Team", "Away Team", "Algorithmic Pick", "Confidence", "Locked Time"])
    df["Confidence"] = df["Confidence"].apply(lambda p: f"{p * 100:.1f}%")
    st.dataframe(df, use_container_width=True)
else:
    st.info("No predictions locked yet. Click **'🚀 Fetch Upcoming Matches'** on the left to scan this week's fixtures.")
