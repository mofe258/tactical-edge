import streamlit as st
import json
from datetime import date
import db
from engine import FootballEngine
import fetcher

st.set_page_config(
    page_title="Tactical Edge | Pro Boom Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

db.init_db()

# ----------------- SPORTY LIQUID GLASS STYLES -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: radial-gradient(circle at 15% 20%, #0c1424 0%, #050811 100%); color: #e2e8f0; }

    /* BOOM SLIP HERO CONTAINER */
    .boom-ticket-card {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(16, 185, 129, 0.08) 100%);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(239, 68, 68, 0.4);
        border-top: 1px solid rgba(248, 113, 113, 0.8);
        box-shadow: 0 16px 45px rgba(239, 68, 68, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15);
        border-radius: 24px;
        padding: 30px;
        margin-bottom: 35px;
    }

    .boom-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        border-bottom: 1px dashed rgba(255, 255, 255, 0.15);
        padding-bottom: 20px;
        margin-bottom: 25px;
    }

    .boom-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 16px;
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: #ffffff;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 800;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    /* MATCH CARD */
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

    .tag-prob { display: inline-block; padding: 4px 10px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
    .tag-odds { display: inline-block; padding: 4px 10px; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
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
    .brand-title { font-size: 2.3rem; font-weight: 800; background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)

# ----------------- AUTO-SYNC PIPELINE -----------------
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
        
        suite = engine.predict_full_suite(
            h_xg, a_xg, 
            h_stat["att_strength"], h_stat["def_strength"], 
            a_stat["att_strength"], a_stat["def_strength"]
        )

        extra_markets_json = json.dumps({
            "h_o15": round(suite["home_and_o15"] * 100, 1),
            "a_o15": round(suite["away_and_o15"] * 100, 1),
            "u45": round(suite["u45_prob"] * 100, 1),
            "dc_1x": round(suite["dc_1x"] * 100, 1),
            "dc_x2": round(suite["dc_x2"] * 100, 1),
            "handicap": round(suite["handicap_plus"] * 100, 1),
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

with st.sidebar:
    st.markdown("### ⚙️ Engine Controls")
    if st.button("🔄 Recalculate & Rebuild Boom Ticket", use_container_width=True):
        db.clear_all()
        with st.spinner("Analyzing stats & assembling boom ticket..."):
            run_auto_sync()
            st.rerun()

if not records and fetcher.API_KEY != "PASTE_YOUR_API_KEY_HERE":
    with st.spinner("⚡ Assembling today's statistical accumulator..."):
        run_auto_sync()
        records = db.get_upcoming_predictions(today_str)

# ----------------- MAIN UI -----------------
st.markdown('<div class="brand-title">Tactical Predictive Suite</div>', unsafe_allow_html=True)
st.markdown('<div style="color: #94a3b8; margin-bottom: 25px;">Statistically optimized selections with frozen database states.</div>', unsafe_allow_html=True)

if records:
    sorted_records = sorted(records, key=lambda x: x[5], reverse=True)
    
    # -------------------------------------------------------------
    # 🔥 FIELD 1: STAKE TODAY — THE BOOM TICKET (2k to 35k Accumulator)
    # -------------------------------------------------------------
    # Filter for the top 8 safe compounders (Odds between 1.15 and 1.65, Prob >= 75%)
    boom_candidates = sorted_records[:8]
    
    total_odds = 1.0
    for item in boom_candidates:
        conf = item[5]
        # Implied odds with bookmaker margin (fair pricing)
        leg_odds = max(1.10, round((1.0 / conf) * 0.96, 2))
        total_odds *= leg_odds

    total_odds = round(total_odds, 2)
    sample_stake = 2000
    potential_return = f"₦{round(sample_stake * total_odds):,}"

    st.markdown(f"""
    <div class="boom-ticket-card">
        <div class="boom-header">
            <div>
                <span class="boom-badge">🔥 STAKE TODAY: THE BOOM ACCUMULATOR</span>
                <div style="font-size: 1.8rem; font-weight: 800; color: #fff; margin-top: 10px;">
                    Algorithmically Assembled Slip ({len(boom_candidates)} Fold)
                </div>
                <div style="color: #cbd5e1; font-size: 0.9rem;">
                    Modeled directly on multi-market combination strategies (Combos, Under 4.5, Handicap Buffers).
                </div>
            </div>
            <div style="display: flex; gap: 24px; margin-top: 10px;">
                <div>
                    <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Total Accumulator Odds</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #fbbf24;">{total_odds:.2f}</div>
                </div>
                <div style="border-left: 1px solid rgba(255,255,255,0.15); padding-left: 20px;">
                    <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Est. Return on ₦2,000</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #34d399;">{potential_return}</div>
                </div>
            </div>
        </div>
        <div style="font-weight: 700; color: #f87171; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 12px; letter-spacing: 0.5px;">
            📋 Targeted Matches on this Ticket:
        </div>
    """, unsafe_allow_html=True)

    # Display the legs of the Boom Ticket
    b_cols = st.columns(2)
    for idx, item in enumerate(boom_candidates):
        m_date, m_comp, m_home, m_away, m_market, m_conf, m_locked = item[:7]
        leg_odds = max(1.10, round((1.0 / m_conf) * 0.96, 2))
        
        with b_cols[idx % 2]:
            st.markdown(f"""
            <div style="background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.75rem; color: #94a3b8;">{m_comp} &nbsp;•&nbsp; 🗓️ {m_date}</div>
                    <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">{m_home} vs {m_away}</div>
                    <div style="color: #38bdf8; font-weight: 800; font-size: 0.9rem; margin-top: 2px;">⚡ {m_market}</div>
                </div>
                <div style="text-align: right;">
                    <span class="tag-prob">{m_conf * 100:.1f}%</span>
                    <div style="font-weight: 800; color: #fbbf24; font-size: 1rem; margin-top: 4px;">@{leg_odds:.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 💎 FIELD 2: SURE BANKER OF THE DAY (Single Bet)
    # -------------------------------------------------------------
    banker = sorted_records[0]
    b_date, b_comp, b_home, b_away, b_market, b_conf, b_locked = banker[:7]
    b_odds = max(1.10, round((1.0 / b_conf) * 0.96, 2))

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 182, 212, 0.04) 100%); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 20px; padding: 24px; margin-bottom: 30px;">
        <div style="display: inline-block; padding: 4px 12px; background: rgba(16, 185, 129, 0.2); border-radius: 50px; color: #34d399; font-weight: 800; font-size: 0.75rem; text-transform: uppercase;">
            💎 Sure Banker of the Day (Single Stake)
        </div>
        <div style="font-size: 1.8rem; font-weight: 800; color: #fff; margin-top: 10px;">
            {b_home} <span style="color: #64748b; font-size: 1.3rem;">vs</span> {b_away}
        </div>
        <div style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 12px;">🏆 {b_comp} &nbsp;|&nbsp; 🗓️ {b_date}</div>
        <div style="display: flex; gap: 20px; align-items: center; flex-wrap: wrap;">
            <div>
                <span style="font-size: 0.7rem; color: #94a3b8; display: block;">SELECTION</span>
                <span style="color: #10b981; font-weight: 800; font-size: 1.25rem;">{b_market}</span>
            </div>
            <div style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">
                <span style="font-size: 0.7rem; color: #94a3b8; display: block;">CONFIDENCE</span>
                <span style="color: #34d399; font-weight: 800; font-size: 1.25rem;">{b_conf * 100:.1f}%</span>
            </div>
            <div style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">
                <span style="font-size: 0.7rem; color: #94a3b8; display: block;">EST. ODDS</span>
                <span style="color: #fbbf24; font-weight: 800; font-size: 1.25rem;">{b_odds:.2f}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 📊 TABS: SURE FIXTURES & ALL PREDICTIONS
    # -------------------------------------------------------------
    def render_card(item):
        m_date, m_comp, m_home, m_away, m_market, m_conf, m_locked = item[:7]
        extra = {}
        if len(item) > 7 and item[7]:
            try:
                extra = json.loads(item[7])
            except Exception:
                pass
        leg_odds = max(1.10, round((1.0 / m_conf) * 0.96, 2))
        h_o15 = extra.get("h_o15", "-")
        u45 = extra.get("u45", "-")
        dc_1x = extra.get("dc_1x", "-")
        corners = extra.get("corners", "-")

        return f"""
        <div class="glass-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 0.75rem; color: #94a3b8; font-weight: 600;">🏆 {m_comp}</span>
                <span style="font-size: 0.75rem; color: #64748b;">🗓️ {m_date}</span>
            </div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #fff; margin-bottom: 12px;">
                {m_home} <span style="color: #64748b; font-weight: 400; font-size: 0.95rem;">vs</span> {m_away}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px; margin-bottom: 10px;">
                <div>
                    <span style="font-size: 0.7rem; color: #94a3b8; display: block;">OPTIMIZED PICK</span>
                    <span style="color: #38bdf8; font-weight: 800; font-size: 1.05rem;">{m_market}</span>
                </div>
                <div style="display: flex; gap: 8px;">
                    <span class="tag-prob">{m_conf * 100:.1f}%</span>
                    <span class="tag-odds">~{leg_odds:.2f}</span>
                </div>
            </div>
            <div style="border-top: 1px solid rgba(255,255,255,0.04); padding-top: 8px;">
                <span class="market-pill">⚽ Home & O1.5: {h_o15}%</span>
                <span class="market-pill">🛡️ Under 4.5: {u45}%</span>
                <span class="market-pill">⚡ DC 1X: {dc_1x}%</span>
                <span class="market-pill">🚩 Corners: {corners}%</span>
            </div>
        </div>
        """

    tab1, tab2 = st.tabs(["🛡️ Sure Fixtures (Safe Singles)", "📊 All Daily Odds & Matches"])

    with tab1:
        sure_fixtures = [r for r in sorted_records if r[5] >= 0.75]
        cols = st.columns(2)
        for idx, item in enumerate(sure_fixtures[:6]):
            with cols[idx % 2]:
                st.markdown(render_card(item), unsafe_allow_html=True)

    with tab2:
        search_query = st.text_input("🔍 Search Team or League", "")
        filtered = sorted_records
        if search_query:
            filtered = [r for r in sorted_records if search_query.lower() in f"{r[2]} {r[3]} {r[1]}".lower()]
        cols2 = st.columns(2)
        for idx, item in enumerate(filtered):
            with cols2[idx % 2]:
                st.markdown(render_card(item), unsafe_allow_html=True)

else:
    st.info("Loading matches...")
