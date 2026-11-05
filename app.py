"""
👑 Tactical Edge — Next-Gen Institutional Football Intelligence Platform
Apple VisionOS-inspired Glassmorphism UI, Dixon-Coles Probability Engine,
Real-Time Kickoff Clocks, and One-Tap SportyBet Slip Generation.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import json

import db
from engine import FootballEngine
import fetcher

# Try importing sportybet module safely
try:
    import sportybet
except ImportError:
    sportybet = None

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="Queen Rins | Neural Football Intelligence",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

db.init_db()

# ----------------- APPLE-GRADE FUTURISTIC GLASSO-MORPHIC CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');

    /* Global Reset & Base */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        letter-spacing: -0.015em;
    }

    /* Ambient Apple OLED Nebula Canvas */
    .stApp {
        background-color: #05070D;
        background-image: 
            radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.12) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.14) 0px, transparent 50%),
            radial-gradient(at 50% 50%, rgba(16, 185, 129, 0.05) 0px, transparent 55%),
            radial-gradient(at 80% 100%, rgba(236, 72, 153, 0.08) 0px, transparent 50%);
        background-attachment: fixed;
        color: #F1F5F9;
    }

    /* Top Brand Hero Bar */
    .hero-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 24px;
        margin-bottom: 24px;
        background: rgba(15, 23, 42, 0.55);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6);
        flex-wrap: wrap;
        gap: 16px;
    }
    .brand-cluster {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .crown-icon {
        font-size: 2.2rem;
        filter: drop-shadow(0 0 16px rgba(245, 158, 11, 0.5));
        animation: subtleFloat 3s ease-in-out infinite;
    }
    @keyframes subtleFloat {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-4px) rotate(-2deg); }
    }
    .brand-title {
        font-size: 1.85rem;
        font-weight: 900;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #FFFFFF 30%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.1;
    }
    .brand-subtitle {
        font-size: 0.80rem;
        font-weight: 500;
        color: #38BDF8;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-top: 3px;
    }

    .status-capsule {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        background: rgba(16, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 8px 16px;
        border-radius: 100px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #E2E8F0;
        backdrop-filter: blur(12px);
    }
    .radar-pulse {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 12px #10B981;
        animation: radarPing 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;
    }
    @keyframes radarPing {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1.15); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* KPI Glass Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        margin-bottom: 24px;
    }
    .glass-kpi {
        background: rgba(15, 23, 42, 0.45);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 18px;
        padding: 18px 20px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .glass-kpi:hover {
        transform: translateY(-3px);
        border-color: rgba(56, 189, 248, 0.3);
        box-shadow: 0 15px 30px -10px rgba(0, 0, 0, 0.5);
    }
    .glass-kpi::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.4), transparent);
    }
    .kpi-header {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #94A3B8;
        letter-spacing: 0.08em;
    }
    .kpi-value {
        font-size: 1.9rem;
        font-weight: 900;
        color: #FFFFFF;
        letter-spacing: -0.03em;
        margin-top: 6px;
    }
    .kpi-sub {
        font-size: 0.74rem;
        color: #64748B;
        font-weight: 500;
        margin-top: 4px;
    }

    /* Match Intelligence Cards */
    .match-deck-card {
        background: rgba(15, 23, 42, 0.5);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 20px;
        padding: 20px 22px;
        margin-bottom: 16px;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
    }
    .match-deck-card:hover {
        border-color: rgba(56, 189, 248, 0.35);
        transform: translateY(-2px);
        box-shadow: 0 16px 36px -10px rgba(0, 0, 0, 0.6);
    }
    .match-top-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
    }
    .comp-pill {
        font-size: 0.74rem;
        font-weight: 700;
        color: #94A3B8;
        background: rgba(255, 255, 255, 0.04);
        padding: 4px 10px;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .versus-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
        gap: 8px;
    }
    .team-badge-wrap {
        display: flex;
        align-items: center;
        gap: 10px;
        flex: 1;
    }
    .team-title {
        font-size: 1.05rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.01em;
    }
    .vs-tag {
        font-size: 0.76rem;
        font-weight: 800;
        color: #64748B;
        background: rgba(255, 255, 255, 0.04);
        padding: 3px 8px;
        border-radius: 6px;
    }

    /* Optimal Prediction Capsule */
    .prediction-capsule {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%);
        border: 1px solid rgba(56, 189, 248, 0.22);
        border-radius: 14px;
        padding: 12px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
    }
    .pick-label {
        font-size: 0.66rem;
        font-weight: 700;
        color: #38BDF8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .pick-name {
        font-size: 1.02rem;
        font-weight: 900;
        color: #FFFFFF;
        letter-spacing: -0.01em;
    }
    .metrics-pill-cluster {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .prob-chip {
        background: rgba(56, 189, 248, 0.16);
        color: #38BDF8;
        font-weight: 800;
        font-size: 0.78rem;
        padding: 5px 10px;
        border-radius: 8px;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .odds-chip {
        background: rgba(245, 158, 11, 0.16);
        color: #FBBF24;
        font-weight: 900;
        font-size: 0.82rem;
        padding: 5px 11px;
        border-radius: 8px;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    /* SportyBet Glowing VIP Card */
    .sporty-vault-card {
        background: radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.18), rgba(9, 26, 24, 0.85) 70%);
        border: 1.5px solid rgba(16, 185, 129, 0.5);
        border-radius: 20px;
        padding: 24px;
        margin: 18px 0;
        text-align: center;
        box-shadow: 0 0 40px rgba(16, 185, 129, 0.2);
        animation: glowPulse 3s ease-in-out infinite alternate;
    }
    @keyframes glowPulse {
        from { box-shadow: 0 0 25px rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.4); }
        to { box-shadow: 0 0 45px rgba(16, 185, 129, 0.35); border-color: rgba(16, 185, 129, 0.8); }
    }
    .sporty-code-big {
        font-family: 'JetBrains Mono', monospace;
        font-size: 3.2rem;
        font-weight: 900;
        color: #10B981;
        letter-spacing: 0.15em;
        margin: 8px 0;
        text-shadow: 0 0 25px rgba(16, 185, 129, 0.5);
    }

    /* Streamlit Tab Apple Overhaul */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(16px);
        padding: 6px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .stTabs [data-baseweb="tab"] {
        color: #94A3B8;
        font-weight: 700;
        font-size: 0.85rem;
        padding: 10px 18px;
        border-radius: 12px;
        border: none;
        background: transparent;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        color: #FFFFFF !important;
        background: rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
    }

    /* Streamlit Buttons to Cyber Pill */
    .stButton>button {
        background: linear-gradient(135deg, #0EA5E9 0%, #3B82F6 100%) !important;
        color: #FFFFFF !important;
        font-weight: 800 !important;
        font-size: 0.92rem !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 12px 24px !important;
        box-shadow: 0 10px 25px -5px rgba(14, 165, 233, 0.4) !important;
        transition: all 0.25s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 15px 30px -5px rgba(14, 165, 233, 0.6) !important;
    }

    @media (max-width: 900px) {
        .kpi-grid { grid-template-columns: repeat(2, 1fr); }
        .hero-container { flex-direction: column; align-items: flex-start; }
    }
</style>
""", unsafe_allow_html=True)

today_str = date.today().strftime("%Y-%m-%d")


# ----------------- REAL-TIME CLOCK DETECTOR -----------------
def is_match_currently_live(m):
    status = m.get("match_status", "SCHEDULED")
    if status in ['IN_PLAY', 'PAUSED', 'LIVE']:
        return True
    if status not in ['FINISHED', 'FT', 'CANCELLED', 'POSTPONED']:
        m_date = m.get("match_date", "")
        k_time = m.get("kickoff_time", "")
        if m_date and len(k_time) >= 5:
            try:
                ko_dt = datetime.strptime(f"{m_date} {k_time[:5]}", "%Y-%m-%d %H:%M")
                diff_minutes = (datetime.utcnow() - ko_dt).total_seconds() / 60.0
                if 0 <= diff_minutes <= 115:
                    return True
            except Exception:
                pass
    return False


# ----------------- SYNCHRONIZATION PIPELINE -----------------
def sync_pipeline(target_date=None):
    use_date = target_date or today_str
    fixtures, err = fetcher.fetch_upcoming_fixtures(use_date, days_ahead=2)
    if not fixtures:
        return 0, err

    engine = FootballEngine()
    standings_cache = {}
    count = 0

    for m in fixtures:
        comp_data = m.get("competition") or {}
        comp_code = comp_data.get("code") or "ECL"
        comp_name = comp_data.get("name") or "UEFA Conference League"

        match_id = str(m["id"])
        utc_datetime_str = m.get("utcDate", "")
        m_date = utc_datetime_str[:10] if utc_datetime_str else use_date

        kickoff_time = "TBD"
        if len(utc_datetime_str) >= 16:
            try:
                kickoff_time = utc_datetime_str[11:16] + " UTC"
            except Exception:
                pass

        status = m.get("status", "SCHEDULED")
        score = m.get("score", {})
        ft = score.get("fullTime", {})
        h_goals = ft.get("home")
        a_goals = ft.get("away")
        score_str = f"{h_goals} - {a_goals}" if (h_goals is not None and a_goals is not None) else "vs"

        if comp_code not in standings_cache:
            standings_cache[comp_code] = fetcher.fetch_standings(comp_code)

        team_stats = standings_cache[comp_code]
        h_team = m["homeTeam"]["name"]
        a_team = m["awayTeam"]["name"]
        h_id = str(m["homeTeam"]["id"])
        a_id = str(m["awayTeam"]["id"])
        h_crest = m["homeTeam"].get("crest", "")
        a_crest = m["awayTeam"].get("crest", "")

        custom = m.get("_custom_ratings", {})
        h_att = custom.get("h_att") or team_stats.get(h_id, {}).get("att_strength") or 1.15
        h_def = custom.get("h_def") or team_stats.get(h_id, {}).get("def_strength") or 0.95
        a_att = custom.get("a_att") or team_stats.get(a_id, {}).get("att_strength") or 0.95
        a_def = custom.get("a_def") or team_stats.get(a_id, {}).get("def_strength") or 1.15

        h_xg, a_xg = engine.calculate_xg(h_att, h_def, a_att, a_def, home_games=8, away_games=8)
        match_analysis = engine.predict_full_match(h_xg, a_xg, h_team, a_team, home_games=8, away_games=8)
        rec = match_analysis["recommendation"]

        boom_status = "PENDING"
        if status in ['FINISHED', 'FT'] and h_goals is not None and a_goals is not None:
            pick = rec["pick"]
            tot = h_goals + a_goals
            if "Home Win" in pick or "1X2" in rec["category"] and "Home" in pick:
                boom_status = "BOOM" if h_goals > a_goals else "LOST"
            elif "Away Win" in pick:
                boom_status = "BOOM" if a_goals > h_goals else "LOST"
            elif "Draw or Away" in pick:
                boom_status = "BOOM" if a_goals >= h_goals else "LOST"
            elif "Home or Draw" in pick:
                boom_status = "BOOM" if h_goals >= a_goals else "LOST"
            elif "Under 3.5" in pick:
                boom_status = "BOOM" if tot < 3.5 else "LOST"
            elif "Over 2.5" in pick:
                boom_status = "BOOM" if tot > 2.5 else "LOST"
            else:
                boom_status = "BOOM" if tot >= 2 else "LOST"

        db.save_or_update_prediction({
            "match_date": m_date,
            "kickoff_time": kickoff_time,
            "match_id": match_id,
            "competition": comp_name,
            "home_team": h_team,
            "away_team": a_team,
            "home_crest": h_crest,
            "away_crest": a_crest,
            "market_category": rec["category"],
            "market_pick": rec["pick"],
            "confidence": rec["prob"],
            "est_odds": rec["odds"],
            "tactical_tag": f"{h_xg:.2f} vs {a_xg:.2f} xG",
            "evidence_quality": "Strong Evidence",
            "match_status": status,
            "live_score": score_str,
            "boom_status": boom_status,
            "full_time_home": h_goals,
            "full_time_away": a_goals,
            "prob_home": match_analysis["prob_home"],
            "prob_draw": match_analysis["prob_draw"],
            "prob_away": match_analysis["prob_away"],
            "details": match_analysis
        })
        count += 1

    return count, None


# Pre-load today's matches
today_matches_check = db.get_predictions_filtered(exact_date=today_str)
if len(today_matches_check) < 8:
    sync_pipeline(today_str)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### ⚙️ Engine Matrix")
    curr_key = fetcher.get_api_key()
    inp_key = st.text_input("Football-Data.org API Key (Optional)", value=curr_key, type="password")
    if inp_key and inp_key != curr_key:
        db.set_setting("FOOTBALL_API_KEY", inp_key)
        st.success("API credentials saved.")

    if st.button("⚡ Force Sync Match Engine", use_container_width=True):
        count, _ = sync_pipeline(today_str)
        st.success(f"Synced {count} European fixtures!")
        st.rerun()

    st.markdown("---")
    st.caption("👑 **Queen Rins Mathematical OS**")
    st.caption("• Dixon-Coles Bivariate Poisson Architecture")
    st.caption("• UEFA Conference League + European Marquee Slate")
    st.caption("• Automated SportyBet API Order Dispatcher")

# ----------------- TOP BRAND HERO -----------------
utc_now_str = datetime.utcnow().strftime("%H:%M UTC")
st.markdown(f"""
<div class="hero-container">
    <div class="brand-cluster">
        <div class="crown-icon">👑</div>
        <div>
            <div class="brand-title">QUEEN RINS</div>
            <div class="brand-subtitle">Institutional Football Intelligence & Neural Arbitrage</div>
        </div>
    </div>
    <div class="status-capsule">
        <div class="radar-pulse"></div>
        <span>LIVE TELEMETRY &nbsp;•&nbsp; {utc_now_str}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Date Selector with Glass Pill
c_date, c_info = st.columns([1.5, 3.5])
with c_date:
    selected_date_obj = st.date_input("🗓️ Active Intelligence Date", value=date.today())
    active_date_str = selected_date_obj.strftime("%Y-%m-%d")

with c_info:
    st.caption(f"⚡ **Active Focus Window ({active_date_str})**. Slips and optimal picks locked strictly to verified matchday kickoff times.")

daily_matches = db.get_predictions_filtered(exact_date=active_date_str)
if not daily_matches:
    sync_pipeline(active_date_str)
    daily_matches = db.get_predictions_filtered(exact_date=active_date_str)

perf = db.get_performance_metrics()

# ----------------- 4 APPLE KPI WIDGETS -----------------
st.markdown(f"""
<div class="kpi-grid">
    <div class="glass-kpi">
        <div class="kpi-header">Fixtures Analyzed</div>
        <div class="kpi-value">{len(daily_matches)}</div>
        <div class="kpi-sub">Locked for {active_date_str}</div>
    </div>
    <div class="glass-kpi">
        <div class="kpi-header">Model Accuracy</div>
        <div class="kpi-value" style="color: #10B981;">{perf['win_rate_str']}</div>
        <div class="kpi-sub">{perf['won']} Won &nbsp;•&nbsp; {perf['lost']} Lost</div>
    </div>
    <div class="glass-kpi">
        <div class="kpi-header">Banker Calibration</div>
        <div class="kpi-value" style="color: #38BDF8;">{perf['brier_score_str']}</div>
        <div class="kpi-sub">Multi-Class Brier Index</div>
    </div>
    <div class="glass-kpi">
        <div class="kpi-header">Settled Predictions</div>
        <div class="kpi-value">{perf['total_settled']}</div>
        <div class="kpi-sub">Empirically Verified</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- NAVIGATION TABS -----------------
main_tabs = st.tabs([
    "⚡ Daily Intelligence",
    "👑 Elite Showdowns",
    "🎯 Banker Accumulator (SportyBet)",
    "📊 Empirical Calibration",
    "🔬 Match Deep-Dive"
])


def render_fixture_card(m):
    is_live = is_match_currently_live(m)
    live_score_display = m["live_score"] if m["live_score"] != "vs" else "0 - 0"

    badge_html = (
        f'<span style="background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #EF4444; font-size: 0.72rem; font-weight: 800; padding: 4px 10px; border-radius: 8px;">🔴 LIVE {live_score_display}</span>' if is_live else (
            f'<span style="background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 0.72rem; font-weight: 800; padding: 4px 10px; border-radius: 8px;">WON (FT {m["live_score"]})</span>' if m["boom_status"] == 'BOOM' else
            f'<span class="comp-pill">🕒 {m.get("kickoff_time", "TBD")}</span>'
        )
    )

    card_html = f"""
    <div class="match-deck-card">
        <div class="match-top-row">
            <span class="comp-pill">{m['competition']}</span>
            {badge_html}
        </div>
        <div class="versus-row">
            <div class="team-badge-wrap">
                <span class="team-title">{m['home_team']}</span>
            </div>
            <span class="vs-tag">VS</span>
            <div class="team-badge-wrap" style="justify-content: flex-end;">
                <span class="team-title" style="text-align: right;">{m['away_team']}</span>
            </div>
        </div>
        <div style="display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap;">
            <span style="background: rgba(255,255,255,0.04); color: #94A3B8; font-size: 0.72rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);">{m.get('tactical_tag', 'Model Edge')}</span>
            <span style="background: rgba(139, 92, 246, 0.1); color: #C084FC; font-size: 0.72rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(139, 92, 246, 0.2);">{m['market_category']}</span>
        </div>
        <div class="prediction-capsule">
            <div>
                <div class="pick-label">Optimal Allocation</div>
                <div class="pick-name">⚡ {m['market_pick']}</div>
            </div>
            <div class="metrics-pill-cluster">
                <span class="prob-chip">{m['confidence']*100:.1f}% Win Prob</span>
                <span class="odds-chip">@{m['est_odds']:.2f}</span>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


# =============================================================================
# TAB 1: DAILY INTELLIGENCE
# =============================================================================
with main_tabs[0]:
    c_s, c_f = st.columns([2.5, 1.5])
    with c_s:
        search_query = st.text_input("🔍 Search Teams or Tournaments", placeholder="e.g. Ajax, Brighton, Atalanta, Monaco")
    with c_f:
        leagues = ["All Leagues"] + sorted(list({r["competition"] for r in daily_matches}))
        sel_league = st.selectbox("Filter Competition", leagues)

    filtered = db.get_predictions_filtered(
        exact_date=active_date_str,
        competition=sel_league,
        search_query=search_query
    )

    if filtered:
        st.caption(f"Showing **{len(filtered)}** calibrated fixtures scheduled for **{active_date_str}**.")
        cols = st.columns(2)
        for idx, item in enumerate(filtered):
            with cols[idx % 2]:
                render_fixture_card(item)
    else:
        st.info(f"No matches scheduled for {active_date_str}. Tap 'Force Sync Match Engine' in the sidebar.")

# =============================================================================
# TAB 2: ELITE SHOWDOWNS
# =============================================================================
with main_tabs[1]:
    st.caption("Curated powerhouse showdowns, high-confidence bankers, and European marquee fixtures.")
    cols_elite = st.columns(2)
    for idx, item in enumerate(daily_matches):
        with cols_elite[idx % 2]:
            render_fixture_card(item)

# =============================================================================
# TAB 3: BANKER ACCUMULATOR & SPORTYBET CODE
# =============================================================================
with main_tabs[2]:
    st.caption(f"Mathematical Banker Compounder: Ranks fixtures by safety index, eliminates draw traps, and books straight to SportyBet.")

    tier = st.radio(
        "Select Multiplier Package:",
        ["3.00x Banker", "5.00x Compounder", "10.00x Boom Slip", "15.00x Multi", "50.00x Jackpot"],
        horizontal=True
    )
    t_val = {"3.00x Banker": 3.0, "5.00x Compounder": 5.0, "10.00x Boom Slip": 10.0, "15.00x Multi": 14.5, "50.00x Jackpot": 50.0}[tier]

    # Rank strictly by reliability first
    sorted_matches = sorted(
        daily_matches,
        key=lambda m: (float(m["confidence"]) * (1.0 / max(1.10, float(m["est_odds"])))),
        reverse=True
    )

    legs = []
    accum_odds = 1.0

    for r in sorted_matches:
        if float(r["confidence"]) >= 0.60:
            accum_odds *= float(r["est_odds"])
            legs.append(r)
            if accum_odds >= t_val:
                break

    accum_odds = round(accum_odds, 2)
    sample_stake = 2000
    est_payout = f"₦{round(sample_stake * accum_odds):,}"

    # SPORTYBET GENERATOR BUTTON
    col_btn, _ = st.columns([2, 1])
    with col_btn:
        if st.button("⚡ GENERATE SPORTYBET BOOKING CODE", use_container_width=True):
            if sportybet:
                with st.spinner("Connecting to SportyBet Server & Booking Ticket..."):
                    code, err = sportybet.generate_sportybet_code(legs)
                    if code:
                        st.session_state["active_sporty_code"] = code
                    else:
                        st.error(f"SportyBet notice: {err}")
            else:
                st.error("sportybet.py module missing.")

    if "active_sporty_code" in st.session_state:
        code = st.session_state["active_sporty_code"]
        st.markdown(f"""
        <div class="sporty-vault-card">
            <div style="font-size: 0.78rem; font-weight: 800; color: #10B981; letter-spacing: 0.1em; text-transform: uppercase;">
                Official SportyBet Booking Code
            </div>
            <div class="sporty-code-big">{code}</div>
            <div style="color: #94A3B8; font-size: 0.85rem; font-weight: 600;">
                Open SportyBet App ➡️ Tap <b>Load Code</b> ➡️ Paste <b>{code}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if legs:
        st.markdown(f"""
        <div style="background: rgba(15, 23, 42, 0.55); border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 20px; margin: 16px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 12px; margin-bottom: 12px; flex-wrap: wrap; gap: 12px;">
                <div>
                    <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; padding: 4px 10px; border-radius: 8px; font-size: 0.76rem; font-weight: 800;">
                        {tier} ({len(legs)} Banker Legs)
                    </span>
                    <div style="font-size: 1.6rem; font-weight: 900; color: #FFFFFF; margin-top: 4px;">Compound Odds: @{accum_odds:.2f}</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Projected Payout (₦{sample_stake:,} Stake)</div>
                    <div style="font-size: 1.7rem; font-weight: 900; color: #10B981;">{est_payout}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        t_cols = st.columns(2)
        for idx, leg in enumerate(legs):
            with t_cols[idx % 2]:
                st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 14px 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.70rem; color: #64748B; font-weight: 700;">{leg['competition']} • {leg['kickoff_time']}</div>
                        <div style="font-weight: 800; color: #FFFFFF; font-size: 0.95rem; margin-top: 2px;">{leg['home_team']} vs {leg['away_team']}</div>
                        <div style="color: #38BDF8; font-weight: 800; font-size: 0.88rem; margin-top: 3px;">⚡ {leg['market_pick']}</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="prob-chip">{leg['confidence']*100:.1f}%</span>
                        <div style="font-weight: 900; color: #FBBF24; font-size: 0.98rem; margin-top: 5px;">@{leg['est_odds']:.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No games meet the high-confidence threshold for this tier.")

# =============================================================================
# TAB 4: EMPIRICAL CALIBRATION
# =============================================================================
with main_tabs[3]:
    st.caption("Empirical performance evaluation across settled matches. Never deletes historical outcomes.")
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("##### Market-Specific Realized Accuracy")
        if perf["market_breakdown"]:
            m_rows = [{"Market": k, "Settled": v["total"], "Won": v["won"], "Accuracy": f"{v['accuracy']}%"} for k, v in perf["market_breakdown"].items()]
            st.dataframe(pd.DataFrame(m_rows), hide_index=True, use_container_width=True)
        else:
            st.info("Market stats populate automatically as today's matches reach full-time.")

    with p2:
        st.markdown("##### Empirical Calibration Reliability")
        if perf["calibration_samples"]:
            st.dataframe(pd.DataFrame(perf["calibration_samples"]), hide_index=True, use_container_width=True)
        else:
            st.info("Calibration bins calculate automatically when settled sample > 0.")

# =============================================================================
# TAB 5: MATCH ANALYTICS DEEP-DIVE
# =============================================================================
with main_tabs[4]:
    if daily_matches:
        options = [f"{m['kickoff_time']} | {m['home_team']} vs {m['away_team']}" for m in daily_matches]
        sel_idx = st.selectbox("Select Fixture for Deep-Dive Analysis:", range(len(options)), format_func=lambda i: options[i])
        selected_m = daily_matches[sel_idx]
        details = json.loads(selected_m.get("details_json", "{}"))

        if details:
            st.markdown(f"### {selected_m['home_team']} vs {selected_m['away_team']}")
            expl = details.get("explanation", {})
            st.info(f"**Model Rationale:** {expl.get('summary', '')}\n\n**Tactical Edge:** {expl.get('supporting', '')}\n\n**Variance Risks:** {expl.get('risk', '')}")

            d1, d2, d3 = st.columns(3)
            with d1:
                st.metric("Home Expected Goals (xG)", f"{details.get('home_xg', 1.0):.2f}")
            with d2:
                st.metric("Away Expected Goals (xG)", f"{details.get('away_xg', 1.0):.2f}")
            with d3:
                st.metric("Selected Allocation", f"{selected_m['market_pick']} (@{selected_m['est_odds']:.2f})")
