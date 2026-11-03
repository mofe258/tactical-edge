import streamlit as st
import json
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

    /* Banker Hero */
    .banker-container {
        position: relative;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.14) 0%, rgba(6, 182, 212, 0.05) 100%);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-top: 1px solid rgba(16, 185, 129, 0.7);
        box-shadow: 0 12px 40px rgba(16, 185, 129, 0.2);
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
    }
    .banker-title { font-size: 2.2rem; font-weight: 800; color: #ffffff; margin-top: 15px; margin-bottom: 5px; }
    .banker-market { font-size: 1.4rem; font-weight: 800; color: #10b981; }

    /* Match Glass Card */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 20px;
        padding: 22px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        margin-bottom: 20px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.4);
    }

    /* Badges & Pills */
    .tag-prob { display: inline-block; padding: 4px 10px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
    .tag-odds { display: inline-block; padding: 4px 10px; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
    
    /* Market Pills Row */
    .market-pill {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 4px 9px;
        border-radius: 6px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #cbd5e1;
        margin-right: 6px;
        margin-top: 6px;
    }
    .brand-title { font-size: 2.1rem; font-weight: 800; background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)

# ----------------- AUTO-PILOT PIPELINE -----------------
today_str = date.today().strftime("%Y-%m-%d")

def run_auto_sync():
    fixtures, err = fetcher.fetch_upcoming_fixtures(today_str, days_ahead=7)
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
            standings_cache[comp_code] = fetcher.fetch_standings(comp_code)
            
        team_stats = standings_cache[comp_code]
        h_team = m["homeTeam"]["name"]
        a_team = m["awayTeam"]["name"]
        
        h_stat = team_stats.get(h_team, {"att_strength": 1.0, "def_strength": 1.0})
        a_stat = team_stats.get(a_team, {"att_strength": 1.0, "def_strength": 1.0})
        
        h_xg, a_xg = engine.calculate_xg(h_stat["att_strength"], h_stat["def_strength"], a_stat["att_strength"], a_stat["def_strength"])
        
        # Run full suite: 1X2, DC, Over/Under, Corners, Cards
        suite = engine.predict_full_suite(
            h_xg, a_xg, 
            h_stat["att_strength"], h_stat["def_strength"], 
            a_stat["att_strength"], a_stat["def_strength"]
        )

        extra_markets_json = json.dumps({
            "o25": round(suite["o25_prob"] * 100, 1),
            "u25": round(suite["u25_prob"] * 100, 1),
            "dc_1x": round(suite["dc_1x_prob"] * 100, 1),
            "dc_x2": round(suite["dc_x2_prob"] * 100, 1),
            "corners": round(suite["corners_prob"] * 100, 1),
            "cards": round(suite["cards_prob"] * 100, 1)
        })

        db.save_prediction(
            m_date, str(m["id"]), m["competition"]["name"], 
            h_team, a_team, suite["best_market"], suite["best_prob"], extra_markets_json
        )
        count += 1
    return count

records = db.get_upcoming_predictions(today_str)

# Sidebar: Controls
with st.sidebar:
    st.markdown("### ⚙️ Engine Controls")
    if st.button("🔄 Recalculate All Markets", use_container_width=True):
        db.clear_all()
        with st.spinner("Re-analyzing all fixtures across all markets..."):
            run_auto_sync()
            st.rerun()

# Auto-sync on fresh launch
if not records and fetcher.API_KEY != "PASTE_YOUR_API_KEY_HERE":
    with st.spinner("⚡ Auto-analyzing matches across Goals, Winners, Corners & Bookings..."):
        run_auto_sync()
        records = db.get_upcoming_predictions(today_str)

# ----------------- MAIN UI -----------------
st.markdown('<div class="brand-title">Tactical Predictive Suite</div>', unsafe_allow_html=True)
st.markdown('<div style="color: #94a3b8; margin-bottom: 25px;">Statistically optimized selections with multi-market distribution.</div>', unsafe_allow_html=True)

def render_match_card(item):
    """Reusable Liquid Glass Match Card with all market stats"""
    m_date, m_comp, m_home, m_away, m_market, m_conf, m_locked = item[:7]
    extra = {}
    if len(item) > 7 and item[7]:
        try:
            extra = json.loads(item[7])
        except Exception:
            pass

    est_odds = max(1.10, round((1.0 / m_conf) * 0.96, 2))
    
    o25 = extra.get("o25", "-")
    dc_1x = extra.get("dc_1x", "-")
    corners = extra.get("corners", "-")
    cards = extra.get("cards", "-")

    return f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 0.75rem; color: #94a3b8; font-weight: 600;">🏆 {m_comp}</span>
            <span style="font-size: 0.75rem; color: #64748b;">🗓️ {m_date}</span>
        </div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #fff; margin-bottom: 12px;">
            {m_home} <span style="color: #64748b; font-weight: 400; font-size: 1rem;">vs</span> {m_away}
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px; margin-bottom: 12px;">
            <div>
                <span style="font-size: 0.7rem; color: #94a3b8; display: block;">PRIME PICK</span>
                <span style="color: #38bdf8; font-weight: 800; font-size: 1.05rem;">{m_market}</span>
            </div>
            <div style="display: flex; gap: 8px;">
                <span class="tag-prob">{m_conf * 100:.1f}%</span>
                <span class="tag-odds">~{est_odds:.2f}</span>
            </div>
        </div>
        <div style="border-top: 1px solid rgba(255,255,255,0.04); padding-top: 8px;">
            <div style="font-size: 0.68rem; color: #64748b; text-transform: uppercase; margin-bottom: 4px;">Market Breakdown:</div>
            <span class="market-pill">⚽ O2.5: {o25}%</span>
            <span class="market-pill">🛡️ DC 1X: {dc_1x}%</span>
            <span class="market-pill">🚩 Corners >8.5: {corners}%</span>
            <span class="market-pill">🟨 Cards >3.5: {cards}%</span>
        </div>
    </div>
    """

if records:
    sorted_records = sorted(records, key=lambda x: x[5], reverse=True)
    
    # 💎 1. SURE BANKER OF THE DAY
    banker = sorted_records[0]
    b_date, b_comp, b_home, b_away, b_market, b_conf, b_locked = banker[:7]
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
            with cols[idx % 2]:
                st.markdown(render_match_card(item), unsafe_allow_html=True)

    with tab2:
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>All matches formatted as Liquid Glass cards with full market metrics.</p>", unsafe_allow_html=True)
        
        search_query = st.text_input("🔍 Search by Team or Competition", "")
        filtered = sorted_records
        if search_query:
            filtered = [r for r in sorted_records if search_query.lower() in f"{r[2]} {r[3]} {r[1]}".lower()]
            
        cols2 = st.columns(2)
        for idx, item in enumerate(filtered):
            with cols2[idx % 2]:
                st.markdown(render_match_card(item), unsafe_allow_html=True)

else:
    st.info("Loading matches...")
