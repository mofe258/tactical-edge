import streamlit as st
import pandas as pd
from datetime import date
import db
from engine import FootballEngine
import fetcher

# Page Configuration
st.set_page_config(page_title="Tactical Edge Predictor", layout="wide", page_icon="⚽")

# Ensure database is initialized with current schema
db.init_db()

st.title("⚽ Tactical Edge - Daily Mathematical Predictions")
st.markdown("Automated algorithmic selections locked before kickoff.")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Read from Streamlit Secrets if available, otherwise allow manual input
    api_key_default = ""
    try:
        if hasattr(st, "secrets") and "FOOTBALL_API_KEY" in st.secrets:
            api_key_default = st.secrets["FOOTBALL_API_KEY"]
    except Exception:
        pass

    api_key = st.text_input("football-data.org API Key", value=api_key_default, type="password")
    min_confidence = st.slider("Min Probability Filter (%)", min_value=60, max_value=85, value=70, step=1) / 100.0
    
    st.divider()
    selected_date = st.date_input("Match Date", value=date.today()).strftime("%Y-%m-%d")
    
    if st.button("🚀 Fetch & Lock Predictions"):
        if not api_key:
            st.error("Please enter your API Key!")
        else:
            with st.spinner("Fetching matches and analyzing stats..."):
                fixtures, err_msg = fetcher.fetch_daily_fixtures(api_key, selected_date)
                
                if err_msg:
                    st.error(err_msg)
                elif not fixtures:
                    st.warning(f"No free-tier matches scheduled for {selected_date}. Try selecting an upcoming match day (e.g. this Saturday)!")
                else:
                    engine = FootballEngine()
                    standings_cache = {}
                    count = 0

                    for m in fixtures:
                        comp_code = m.get("competition", {}).get("code")
                        if not comp_code:
                            continue
                        
                        # Cache standings per competition to prevent hitting rate limits
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
                        
                        # Pick the highest probability outcome
                        safest_market = max(probs, key=probs.get)
                        safest_prob = probs[safest_market]

                        if safest_prob >= min_confidence:
                            db.save_prediction(
                                selected_date, 
                                str(m["id"]), 
                                m["competition"]["name"],
                                h_team, 
                                a_team, 
                                safest_market, 
                                safest_prob
                            )
                            count += 1
                    
                    if count > 0:
                        st.success(f"Analysis complete! Locked {count} high-confidence picks.")
                        st.rerun()
                    else:
                        st.info("Matches found, but none met your minimum confidence threshold. Try lowering the filter.")

# Display Area (Read-Only from SQLite)
raw_data = db.get_predictions(selected_date)

if raw_data:
    df = pd.DataFrame(raw_data, columns=["Competition", "Home Team", "Away Team", "Safest Pick", "Model Probability", "Locked At"])
    df["Model Probability"] = df["Model Probability"].apply(lambda p: f"{p * 100:.1f}%")
    st.subheader(f"Locked Selections for {selected_date}")
    st.dataframe(df, use_container_width=True)
else:
    st.info(f"No predictions locked for {selected_date}. Enter your API key on the left, choose a match day, and click **'Fetch & Lock Predictions'**.")
