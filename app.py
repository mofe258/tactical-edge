import streamlit as st
import pandas as pd
from datetime import date
import sqlite3
import db
from engine import FootballEngine
import fetcher

# Page Setup
st.set_page_config(
    page_title="Tactical Edge | Liquid Betting Engine",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

db.init_db()

# ----------------- LIQUID GLASSMORPHISM STYLING -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Main background */
    .stApp {
        background: radial-gradient(circle at 15% 20%, #0d1527 0%, #060913 100%);
        color: #e2e8f0;
    }

    /* Sidebar Glass */
    section[data-testid="stSidebar"] {
        background: rgba(13, 21, 39, 0.6) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    /* Banker Hero Card */
    .banker-container {
        position: relative;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 182, 212, 0.04) 100%);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-top: 1px solid rgba(16, 185, 129, 0.7);
        box-shadow: 0 12px 40px rgba(16, 185, 129, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.2);
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

    .banker-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #ffffff;
        margin-top: 15px;
        margin-bottom: 5px;
        letter-spacing: -0.5px;
    }

    .banker-market {
        font-size: 1.35rem;
        font-weight: 700;
        color: #10b981;
    }

    /* Standard Glass Card */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-top: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
        margin-bottom: 16px;
    }

    .glass-card:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.4);
    }

    /* Metric Badges */
    .tag-prob {
        display: inline-block;
        padding: 4px 10px;
        background: rgba(56, 189, 248, 0.15);
        border: 1px solid rgba(56, 189, 248, 0.4);
        color: #38bdf8;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.85rem;
    }

    .tag-odds {
        display: inline-block;
        padding: 4px 10px;
        background: rgba(245, 158, 11, 0.15);
        border: 1px solid rgba(245, 158, 11, 0.4);
        color: #fbbf24;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.85rem;
    }

    /* Header Brand */
    .brand-title {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    # Custom Brand Logo Badge
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
        <svg width="42" height="42" viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="12" fill="url(#brandGrad)"/>
            <path d="M20 9L29 14.5V25.5L20 31L11 25.5V14.5L20 9Z" stroke="#ffffff" stroke-width="2" stroke-linejoin="round"/>
            <circle cx="20" cy="20" r="3.5" fill="#34d399"/>
            <defs>
                <linearGradient id="brandGrad" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#10b981"/>
                    <stop offset="1" stop-color="#0284c7"/>
                </linearGradient>
            </defs>
        </svg>
        <div>
            <div style="font-weight: 800; font-size: 1.15rem; color: #fff; letter-spacing: -0.5px;">TACTICAL EDGE</div>
            <div style="font-size: 0.7rem; color: #94a3b8; letter-spacing: 1px; text-transform: uppercase;">Quant Predictions</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    api_key_default = ""
    try:
        if hasattr(st, "secrets") and "FOOTBALL_API_KEY" in st.secrets:
            api_key_default = st.secrets["FOOTBALL_API_KEY"]
    except Exception:
        pass

    api_key = st.text_input("football-data.org API Key", value=api_key_default, type="password")
    
    min_confidence = st.slider("Precision Threshold (%)", min_value=65, max_value=85, value=70, step=1) / 100.0
    scan_days = st.selectbox("Scan Horizon", [3, 5, 7], index=2, format_func=lambda x: f"Next {x} Days")
    start_date = st.date_input("From Date", value=date.today()).strftime("%Y-%m-%d")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⚡ Sync & Lock Fixtures", use_container_width=True):
        if not api_key:
            st.error("Please insert your API Key.")
        else:
            with st.spinner("Analyzing stats, form decay, & computing markets..."):
                fixtures, err_msg = fetcher.fetch_upcoming_fixtures(api_key, start_date, days_ahead=scan_days)
                
                if err_msg:
                    st.error(err_msg)
                elif not fixtures:
                    st.warning("No matches scheduled across eligible competitions.")
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
                        st.success(f"Success! {count} edge markets computed and locked.")
                        st.rerun()
                    else:
                        st.info("No fixtures exceeded the confidence filter. Try adjusting the slider.")

# ----------------- MAIN INTERFACE -----------------
st.markdown('<div class="brand-title">Tactical Predictive Suite</div>', unsafe_allow_html=True)
st.markdown('<div style="color: #94a3b8; margin-bottom: 25px;">Statistically optimized selections with frozen database states.</div>', unsafe_allow_html=True)

# Fetch all locked predictions from SQLite
conn = sqlite3.connect(db.DB_NAME)
c = conn.cursor()
c.execute("SELECT match_date, competition, home_team, away_team, market, confidence, locked_at FROM predictions ORDER BY confidence DESC")
all_records = c.fetchall()
conn.close()

if all_records:
    # 1. SURE BANKER OF THE DAY (Highest Probability Pick)
    banker = all_records[0]
    b_date, b_comp, b_home, b_away, b_market, b_conf, b_locked = banker
    # Implied Bookmaker Odds estimate (1 / prob + bookmaker margin)
    b_odds = round((1.0 / b_conf) * 0.96, 2)
    b_odds = max(1.10, b_odds)

    st.markdown(f"""
    <div class="banker-container">
        <div class="banker-badge">💎 Sure Banker of the Day</div>
        <div class="banker-title">{b_home} <span style="color: #64748b; font-weight: 400; font-size: 1.6rem;">vs</span> {b_away}</div>
        <div style="color: #cbd5e1; font-size: 0.95rem; margin-bottom: 18px;">
            🏆 {b_comp} &nbsp;|&nbsp; 🗓️ {b_date} &nbsp;|&nbsp; 🔒 Locked at {b_locked}
        </div>
        <div style="display: flex; align-items: center; gap: 20px; flex-wrap: wrap;">
            <div>
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px;">Algorithmic Pick</div>
                <div class="banker-market">{b_market}</div>
            </div>
            <div style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px;">Model Confidence</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #34d399;">{b_conf * 100:.1f}%</div>
            </div>
            <div style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px;">Est. Fair Odds</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #fbbf24;">{b_odds:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. TABS: SURE FIXTURES & ALL PREDICTIONS
    tab1, tab2 = st.tabs(["🛡️ Sure Fixtures (Top Edge Accumulator)", "📊 All Daily Odds & Predictions"])

    with tab1:
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Picks with confidence exceeding 75% for building low-variance accumulators.</p>", unsafe_allow_html=True)
        
        # Take picks ranked 2 through 7 (or high confidence)
        sure_fixtures = [r for r in all_records if r[5] >= 0.75]
        
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
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Complete database of all analyzed fixtures with computed odds.</p>", unsafe_allow_html=True)
        
        # Prepare full dataframe with calculated odds
        table_rows = []
        for r in all_records:
            m_date, m_comp, m_home, m_away, m_market, m_conf, m_locked = r
            odds = max(1.10, round((1.0 / m_conf) * 0.96, 2))
            table_rows.append({
                "Date": m_date,
                "Competition": m_comp,
                "Matchup": f"{m_home} vs {m_away}",
                "Prediction": m_market,
                "Probability": f"{m_conf * 100:.1f}%",
                "Est. Odds": f"{odds:.2f}",
                "Locked At": m_locked
            })
        
        df_full = pd.DataFrame(table_rows)
        
        # Search & Filter
        search_query = st.text_input("🔍 Search by Team or Competition", "")
        if search_query:
            df_full = df_full[df_full['Matchup'].str.contains(search_query, case=False) | df_full['Competition'].str.contains(search_query, case=False)]
            
        st.dataframe(df_full, use_container_width=True, hide_index=True)

else:
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 50px 20px;">
        <div style="font-size: 2.5rem; margin-bottom: 15px;">🔮</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #ffffff;">No Active Daily Predictions</div>
        <div style="color: #94a3b8; font-size: 0.9rem; max-width: 450px; margin: 10px auto 25px auto;">
            Enter your API Key in the left sidebar and click <b>⚡ Sync & Lock Fixtures</b> to run the algorithms.
        </div>
    </div>
    """, unsafe_allow_html=True)
