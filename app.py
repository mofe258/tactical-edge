import streamlit as st
import pandas as pd
from datetime import date
import db
from engine import FootballEngine
import fetcher

st.set_page_config(
    page_title="Tactical Edge | Liquid Betting Engine",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

db.init_db()

# ----------------- LIQUID GLASS STYLES -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: radial-gradient(circle at 15% 20%, #0d1527 0%, #060913 100%); color: #e2e8f0; }

    .banker-container {
        position: relative;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 182, 212, 0.04) 100%);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-top: 1px solid rgba(16, 185, 129, 0.7);
        box-shadow: 0 12px 40px rgba(16, 185, 129, 0.18);
        border-radius: 24px;
        padding: 28px;
        margin-bottom: 30px;
    }
    .banker-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid rgba(16, 185, 129, 0.5);
        color: #34d399;
        border-radius: 50px;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .banker-title { font-size: 2.2rem; font-weight: 800; color: #ffffff; margin-top: 15px; margin-bottom: 5px; }
    .banker-market { font-size: 1.4rem; font-weight: 800; color: #10b981; }

    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-top: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        margin-bottom: 16px;
    }
    .tag-prob { display: inline-block; padding: 4px 10px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
    .tag-odds { display: inline-block; padding: 4px 10px; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
    .brand-title { font-size: 2.1rem; font-weight: 800; background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)

# ----------------- SAFE API KEY RETRIEVAL -----------------
saved_api_key = ""
if hasattr(db, "get_setting"):
    saved_api_key = db.get_setting("FOOTBALL_API_KEY", "")

if not saved_api_key:
    try:
        if hasattr(st, "secrets") and "FOOTBALL_API_KEY" in st.secrets:
            saved_api_key = st.secrets["FOOTBALL_API_KEY"]
    except Exception:
        pass

with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    input_key = st.text_input("football-data.org API Key", value=saved_api_key, type="password")
    if input_key and input_key != saved_api_key:
        if hasattr(db, "set_setting"):
            db.set_setting("FOOTBALL_API_KEY", input_key)
        saved_api_key = input_key
        st.success("API Key saved permanently!")

    min_confidence = st.slider("Min Probability Threshold (%)", min_value=60, max_value=85, value=70, step=1) / 100.0
    scan_days = 7
    today_str = date.today().strftime("%Y-%m-%d")

    st.markdown("---")
    st.caption("🟢 **Auto-Pilot:** Active\n\nPicks update automatically in the background.")
    if st.button("🔄 Force Refresh Cache"):
        st.session_state["force_refresh"] = True
        st.rerun()

# ----------------- AUTO-PILOT PIPELINE -----------------
def execute_auto_sync(api_key, start_date, days_ahead, threshold):
    fixtures, err = fetcher.fetch_upcoming_fixtures(api_key, start_date, days_ahead=days_ahead)
    if err or not fixtures:
        return 0
    engine = FootballEngine()
    standings_cache = {}
    count = 0
    for m in fixtures:
        comp_code = m.get("competition", {}).get("code")
        if not comp_code:
            continue
        m_date = m.get("utcDate", "")[:10]
        if comp_code not in standings_cache:
            standings_cache[comp_code] = fetcher.fetch_standings(api_key, comp_code)
            
        team_stats = standings_cache[comp_code]
        h_team = m["homeTeam"]["name"]
        a_team = m["awayTeam"]["name"]
        
        h_stat = team_stats.get(h_team, {"att_strength": 1.0, "def_strength": 1.0})
        a_stat = team_stats.get(a_team, {"att_strength": 1.0, "def_strength": 1.0})
        
        h_xg, a_xg = engine.calculate_xg(h_stat["att_strength"], h_stat["def_strength"], a_stat["att_strength"], a_stat["def_strength"])
        probs = engine.predict_match(h_xg, a_xg)
        safest_market = max(probs, key=probs.get)
        safest_prob = probs[safest_market]

        if safest_prob >= threshold:
            db.save_prediction(m_date, str(m["id"]), m["competition"]["name"], h_team, a_team, safest_market, safest_prob)
            count += 1
    return count

# Fetch existing predictions safely
today_str = date.today().strftime("%Y-%m-%d")
records = []
if hasattr(db, "get_upcoming_predictions"):
    records = db.get_upcoming_predictions(today_str)

# Auto-Sync trigger if empty or forced
if (not records or st.session_state.get("force_refresh", False)) and saved_api_key:
    st.session_state["force_refresh"] = False
    with st.spinner("⚡ Auto-analyzing matches and locking today's daily predictions..."):
        execute_auto_sync(saved_api_key, today_str, scan_days, min_confidence)
        if hasattr(db, "get_upcoming_predictions"):
            records = db.get_upcoming_predictions(today_str)

# ----------------- MAIN DISPLAY -----------------
st.markdown('<div class="brand-title">Tactical Predictive Suite</div>', unsafe_allow_html=True)
st.markdown('<div style="color: #94a3b8; margin-bottom: 25px;">Statistically optimized selections with immutable database locks.</div>', unsafe_allow_html=True)

if records:
    sorted_records = sorted(records, key=lambda x: x[5], reverse=True)
    
    # 💎 1. SURE BANKER OF THE DAY
    banker = sorted_records[0]
    b_date, b_comp, b_home, b_away, b_market, b_conf, b_locked = banker
    b_odds = max(1.10, round((1.0 / b_conf) * 0.96, 2))

    st.markdown(f"""
    <div class="banker-container">
        <div class="banker-badge">💎 Sure Banker of the Day</div>
        <div class="banker-title">{b_home} <span style="color: #64748b; font-weight: 400; font-size: 1.6rem;">vs</span> {b_away}</div>
        <div style="color: #cbd5e1; font-size: 0.95rem; margin-bottom: 18px;">
            🏆 {b_comp} &nbsp;|&nbsp; 🗓️ {b_date} &nbsp;|&nbsp; 🔒 Locked at {b_locked}
        </div>
        <div style="display: flex; align-items: center; gap: 24px; flex-wrap: wrap;">
            <div>
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #94a3b8;">Algorithmic Selection</div>
                <div class="banker-market">{b_market}</div>
            </div>
            <div style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #94a3b8;">Model Confidence</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: #34d399;">{b_conf * 100:.1f}%</div>
            </div>
            <div style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #94a3b8;">Est. Fair Odds</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: #fbbf24;">{b_odds:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. TABS
    tab1, tab2 = st.tabs(["🛡️ Sure Fixtures (Safe Multi-Bet)", "📊 Daily Odds & Predictions Board"])

    with tab1:
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Selections exceeding 75% probability for building low-variance accumulators.</p>", unsafe_allow_html=True)
        sure_fixtures = [r for r in sorted_records if r[5] >= 0.75]
        
        cols = st.columns(2)
        for idx, item in enumerate(sure_fixtures[:6]):
            m_date, m_comp, m_home, m_away, m_market, m_conf, m_locked = item
            est_odds = max(1.10, round((1.0 / m_conf) * 0.96, 2))
            
            with cols[idx % 2]:
                st.markdown(f"""
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 0.75rem; color: #94a3b8; font-weight: 600;">{m_comp}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">🗓️ {m_date}</span>
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 12px;">
                        {m_home} <span style="color: #64748b; font-weight: 400;">vs</span> {m_away}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px;">
                        <div>
                            <span style="font-size: 0.7rem; color: #94a3b8; display: block;">SELECTION</span>
                            <span style="color: #38bdf8; font-weight: 700; font-size: 0.95rem;">{m_market}</span>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <span class="tag-prob">{m_conf * 100:.1f}%</span>
                            <span class="tag-odds">~{est_odds:.2f}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab2:
        table_rows = []
        for r in sorted_records:
            m_date, m_comp, m_home, m_away, m_market, m_conf, m_locked = r
            odds = max(1.10, round((1.0 / m_conf) * 0.96, 2))
            table_rows.append({
                "Date": m_date,
                "Competition": m_comp,
                "Matchup": f"{m_home} vs {m_away}",
                "Market Selection": m_market,
                "Probability": f"{m_conf * 100:.1f}%",
                "Est. Odds": f"{odds:.2f}",
                "Locked At": m_locked
            })
        
        df_full = pd.DataFrame(table_rows)
        search_query = st.text_input("🔍 Search by Team or Competition", "")
        if search_query:
            df_full = df_full[df_full['Matchup'].str.contains(search_query, case=False) | df_full['Competition'].str.contains(search_query, case=False)]
            
        st.dataframe(df_full, use_container_width=True, hide_index=True)

else:
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 50px 20px;">
        <div style="font-size: 2.5rem; margin-bottom: 15px;">⚡</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #ffffff;">Auto-Pilot Ready</div>
        <div style="color: #94a3b8; font-size: 0.9rem; max-width: 450px; margin: 10px auto 15px auto;">
            Paste your API key once in the sidebar. The engine will permanently store it and automatically load matches on arrival.
        </div>
    </div>
    """, unsafe_allow_html=True)
