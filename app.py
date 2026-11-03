import streamlit as st
import json
from datetime import date
import db
from engine import FootballEngine
import fetcher

# App Configuration
st.set_page_config(
    page_title="Tactical Edge | Multi-Odds Boom Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

db.init_db()

# Auto-purge old single-market cache so new SportyBet combo picks load immediately
ENGINE_VERSION = "v4_sporty_multitier"
if db.get_setting("engine_version") != ENGINE_VERSION:
    db.clear_all()
    db.set_setting("engine_version", ENGINE_VERSION)

# ----------------- LIQUID GLASS STYLES -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: radial-gradient(circle at 15% 20%, #0c1424 0%, #050811 100%); color: #e2e8f0; }

    /* Glass Ticket Hero */
    .ticket-hero {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(16, 185, 129, 0.08) 100%);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(239, 68, 68, 0.4);
        border-top: 1px solid rgba(248, 113, 113, 0.8);
        border-radius: 24px;
        padding: 26px;
        margin-bottom: 25px;
    }

    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 20px;
        padding: 22px;
        margin-bottom: 18px;
    }

    .tag-prob { display: inline-block; padding: 4px 10px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
    .tag-odds { display: inline-block; padding: 4px 10px; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
    .market-pill { display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 4px 8px; border-radius: 6px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #cbd5e1; margin-right: 4px; margin-top: 4px; }
    .brand-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)

# ----------------- DATA PIPELINE -----------------
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
        suite = engine.predict_full_suite(h_xg, a_xg, h_stat["att_strength"], h_stat["def_strength"], a_stat["att_strength"], a_stat["def_strength"])

        extra_markets_json = json.dumps({
            "h_o15": round(suite["h_o15"] * 100, 1),
            "a_o15": round(suite["a_o15"] * 100, 1),
            "u45": round(suite["u45"] * 100, 1),
            "dc_x2": round(suite["dc_x2"] * 100, 1),
            "handicap": round(suite["handicap"] * 100, 1),
            "o15": round(suite["o15"] * 100, 1),
            "o05": round(suite["o05"] * 100, 1)
        })

        db.save_prediction(
            m_date, str(m["id"]), m["competition"]["name"], 
            h_team, a_team, suite["best_market"], suite["best_prob"], suite["est_odds"], extra_markets_json
        )
        count += 1
    return count

records = db.get_upcoming_predictions(today_str)

if not records and fetcher.API_KEY != "PASTE_YOUR_API_KEY_HERE":
    with st.spinner("⚡ Running multi-market algorithm across scheduled fixtures..."):
        run_auto_sync()
        records = db.get_upcoming_predictions(today_str)

# ----------------- MAIN INTERFACE -----------------
st.markdown('<div class="brand-title">Tactical Predictive Suite</div>', unsafe_allow_html=True)
st.markdown('<div style="color: #94a3b8; margin-bottom: 20px;">Precision sports analytics modeled on high-yield accumulator compounding.</div>', unsafe_allow_html=True)

if records:
    sorted_records = sorted(records, key=lambda x: x[5], reverse=True)

    # 4 DEDICATED SECTIONS
    main_tabs = st.tabs([
        "🔥 Odds Tier Accumulator (3, 5, 10, 20, 100)",
        "🎯 Sure Banger Hits (Lock-In Singles)",
        "🛡️ Sure Fixtures (Detailed Staking Signals)",
        "📊 All Daily Matches & Markets"
    ])

    # =========================================================================
    # TAB 1: ODDS TIER ACCUMULATOR BUILDER (3, 5, 10, 20, 100 ODDS)
    # =========================================================================
    with main_tabs[0]:
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Select your targeted odds tier. The engine automatically compounds high-conviction legs to match your desired slip.</p>", unsafe_allow_html=True)
        
        tier = st.radio("Choose Target Odds:", ["3 Odds", "5 Odds", "10 Odds", "20 Odds", "100 Odds"], horizontal=True)
        
        target_dict = {"3 Odds": 3.0, "5 Odds": 5.0, "10 Odds": 10.0, "20 Odds": 20.0, "100 Odds": 100.0}
        target_val = target_dict[tier]

        # Assemble accumulator legs to meet target
        selected_legs = []
        current_odds = 1.0

        for r in sorted_records:
            leg_odds = r[6]
            selected_legs.append(r)
            current_odds *= leg_odds
            if current_odds >= target_val:
                break

        current_odds = round(current_odds, 2)
        
        # Suggested stake based on odds tier
        rec_stakes = {"3 Odds": 10000, "5 Odds": 5000, "10 Odds": 2000, "20 Odds": 2000, "100 Odds": 500}
        stake = rec_stakes[tier]
        est_return = f"₦{round(stake * current_odds):,}"

        st.markdown(f"""
        <div class="ticket-hero">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; border-bottom: 1px dashed rgba(255,255,255,0.15); padding-bottom: 16px; margin-bottom: 20px;">
                <div>
                    <span style="background: #ef4444; color: #fff; padding: 4px 12px; border-radius: 50px; font-weight: 800; font-size: 0.75rem; text-transform: uppercase;">
                        🔥 {tier} Accumulator Slip ({len(selected_legs)} Fold)
                    </span>
                    <div style="font-size: 1.6rem; font-weight: 800; color: #fff; margin-top: 8px;">Targeted Multi-Bet Package</div>
                </div>
                <div style="display: flex; gap: 24px;">
                    <div>
                        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Total Slip Odds</div>
                        <div style="font-size: 2rem; font-weight: 800; color: #fbbf24;">{current_odds:.2f}</div>
                    </div>
                    <div style="border-left: 1px solid rgba(255,255,255,0.15); padding-left: 20px;">
                        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Est. Return on ₦{stake:,}</div>
                        <div style="font-size: 2rem; font-weight: 800; color: #34d399;">{est_return}</div>
                    </div>
                </div>
            </div>
            <div style="font-size: 0.8rem; font-weight: 700; color: #f87171; text-transform: uppercase; margin-bottom: 12px;">
                📋 Matches on this {tier} Ticket:
            </div>
        """, unsafe_allow_html=True)

        t_cols = st.columns(2)
        for idx, item in enumerate(selected_legs):
            m_date, m_comp, m_home, m_away, m_market, m_conf, m_odds = item[:7]
            with t_cols[idx % 2]:
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.7rem; color: #94a3b8;">{m_comp} &nbsp;•&nbsp; 🗓️ {m_date}</div>
                        <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">{m_home} vs {m_away}</div>
                        <div style="color: #38bdf8; font-weight: 800; font-size: 0.9rem; margin-top: 2px;">⚡ {m_market}</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="tag-prob">{m_conf * 100:.1f}%</span>
                        <div style="font-weight: 800; color: #fbbf24; font-size: 1rem; margin-top: 4px;">@{m_odds:.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: SURE BANGER HITS (LOCK-IN SINGLES & DOUBLE COMBOS)
    # =========================================================================
    with main_tabs[1]:
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Dedicated to individual lock-in selections. Use these for heavy single stakes or conservative rollovers.</p>", unsafe_allow_html=True)
        
        # Take the top 6 highest certainty matches
        bangers = sorted_records[:6]
        
        b_cols = st.columns(2)
        for idx, item in enumerate(bangers):
            m_date, m_comp, m_home, m_away, m_market, m_conf, m_odds = item[:7]
            extra = json.loads(item[8]) if len(item) > 8 and item[8] else {}
            o15 = extra.get("o15", "92.0")
            o05 = extra.get("o05", "99.0")
            
            with b_cols[idx % 2]:
                st.markdown(f"""
                <div class="glass-card" style="border-left: 4px solid #10b981;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 0.75rem; color: #94a3b8;">🏆 {m_comp}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">🗓️ {m_date}</span>
                    </div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #fff; margin-bottom: 10px;">
                        {m_home} <span style="color: #64748b; font-size: 1rem;">vs</span> {m_away}
                    </div>
                    <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 0.65rem; color: #94a3b8; text-transform: uppercase;">🎯 BANGER SELECTION</div>
                            <div style="color: #34d399; font-weight: 800; font-size: 1.1rem;">{m_market}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #fbbf24; font-weight: 800; font-size: 1.1rem;">@{m_odds:.2f}</div>
                            <div style="color: #38bdf8; font-weight: 700; font-size: 0.75rem;">{m_conf * 100:.1f}% Confidence</div>
                        </div>
                    </div>
                    <div style="border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px;">
                        <span style="font-size: 0.7rem; color: #94a3b8; display: block; margin-bottom: 4px;">ALTERNATE ULTRA-SAFE COVERS:</span>
                        <span class="market-pill">⚽ Over 1.5 Goals: {o15}%</span>
                        <span class="market-pill">🔒 Over 0.5 Goals: {o05}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 3: SURE FIXTURES (DETAILED STAKING SIGNALS)
    # =========================================================================
    with main_tabs[2]:
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Detailed tactical cards specifying exactly what market to stake, backup options, and edge metrics.</p>", unsafe_allow_html=True)

        s_cols = st.columns(2)
        for idx, item in enumerate(sorted_records[:8]):
            m_date, m_comp, m_home, m_away, m_market, m_conf, m_odds = item[:7]
            extra = json.loads(item[8]) if len(item) > 8 and item[8] else {}
            h_o15 = extra.get("h_o15", "-")
            u45 = extra.get("u45", "-")
            dc_x2 = extra.get("dc_x2", "-")
            hcap = extra.get("handicap", "-")

            with s_cols[idx % 2]:
                st.markdown(f"""
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 0.75rem; color: #94a3b8;">🏆 {m_comp}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">🗓️ {m_date}</span>
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #fff; margin-bottom: 12px;">
                        {m_home} <span style="color: #64748b; font-weight: 400; font-size: 0.95rem;">vs</span> {m_away}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px; margin-bottom: 10px;">
                        <div>
                            <span style="font-size: 0.68rem; color: #94a3b8; display: block;">RECOMMENDED BET</span>
                            <span style="color: #38bdf8; font-weight: 800; font-size: 1.05rem;">{m_market}</span>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <span class="tag-prob">{m_conf * 100:.1f}%</span>
                            <span class="tag-odds">@{m_odds:.2f}</span>
                        </div>
                    </div>
                    <div style="border-top: 1px solid rgba(255,255,255,0.04); padding-top: 8px;">
                        <span class="market-pill">⚽ Home & O1.5: {h_o15}%</span>
                        <span class="market-pill">🛡️ Under 4.5: {u45}%</span>
                        <span class="market-pill">⚡ DC (X2): {dc_x2}%</span>
                        <span class="market-pill">🛡️ Away (+3) Hcap: {hcap}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 4: ALL DAILY MATCHES & MARKETS
    # =========================================================================
    with main_tabs[3]:
        search_query = st.text_input("🔍 Filter by Team or Competition", "")
        filtered = sorted_records
        if search_query:
            filtered = [r for r in sorted_records if search_query.lower() in f"{r[2]} {r[3]} {r[1]}".lower()]

        cols_all = st.columns(2)
        for idx, item in enumerate(filtered):
            m_date, m_comp, m_home, m_away, m_market, m_conf, m_odds = item[:7]
            with cols_all[idx % 2]:
                st.markdown(f"""
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <span style="font-size: 0.75rem; color: #94a3b8;">{m_comp}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">🗓️ {m_date}</span>
                    </div>
                    <div style="font-weight: 700; color: #fff; font-size: 1.1rem; margin-bottom: 8px;">
                        {m_home} vs {m_away}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px;">
                        <span style="color: #34d399; font-weight: 800; font-size: 0.95rem;">{m_market}</span>
                        <div>
                            <span class="tag-prob">{m_conf * 100:.1f}%</span>
                            <span class="tag-odds">@{m_odds:.2f}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

else:
    st.info("⚡ Analyzing upcoming matches and building multi-odds packages...")
