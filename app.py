"""
👑 QUEEN RINS — Next-Gen Institutional Football Intelligence
Live ESPN Score Tracking, Chaos-Proof Asian Handicaps & DNB Markets,
Automatic Settlement Verification, and ₦100 ➔ ₦70k Slip Generator.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
import json

import db
from engine import FootballEngine
import fetcher

try:
    import sportybet
except ImportError:
    sportybet = None

st.set_page_config(
    page_title="Queen Rins | Neural Football Intelligence",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

db.init_db()

# ----------------- APPLE-GRADE FUTURISTIC CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: #05070D;
        background-image: 
            radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.12) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.14) 0px, transparent 50%),
            radial-gradient(at 50% 50%, rgba(16, 185, 129, 0.05) 0px, transparent 55%);
        background-attachment: fixed;
        color: #F1F5F9;
    }

    .hero-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 24px;
        margin-bottom: 24px;
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(24px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6);
        flex-wrap: wrap;
        gap: 16px;
    }
    .brand-title {
        font-size: 1.85rem;
        font-weight: 900;
        background: linear-gradient(135deg, #FFFFFF 30%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .status-capsule {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        background: rgba(16, 24, 39, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 8px 16px;
        border-radius: 100px;
        font-size: 0.78rem;
        font-weight: 700;
        color: #E2E8F0;
    }
    .radar-pulse {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 12px #10B981;
    }

    .match-deck-card {
        background: rgba(15, 23, 42, 0.5);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 20px;
        padding: 20px 22px;
        margin-bottom: 16px;
        transition: all 0.25s ease;
    }
    .match-deck-card:hover {
        border-color: rgba(56, 189, 248, 0.35);
        transform: translateY(-2px);
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
    }

    .versus-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
        gap: 8px;
    }
    .team-title {
        font-size: 1.05rem;
        font-weight: 800;
        color: #FFFFFF;
    }
    .vs-tag {
        font-size: 0.95rem;
        font-weight: 900;
        color: #38BDF8;
        background: rgba(56, 189, 248, 0.12);
        padding: 5px 14px;
        border-radius: 8px;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }

    .prediction-capsule {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 14px;
        padding: 14px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
    }
    .pick-label {
        font-size: 0.68rem;
        font-weight: 800;
        color: #38BDF8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .pick-name {
        font-size: 1.1rem;
        font-weight: 900;
        color: #FFFFFF;
    }
    .prob-chip {
        background: rgba(56, 189, 248, 0.16);
        color: #38BDF8;
        font-weight: 800;
        font-size: 0.80rem;
        padding: 5px 10px;
        border-radius: 8px;
    }
    .odds-chip {
        background: rgba(245, 158, 11, 0.16);
        color: #FBBF24;
        font-weight: 900;
        font-size: 0.90rem;
        padding: 5px 12px;
        border-radius: 8px;
    }

    .sporty-vault-card {
        background: radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.2), rgba(9, 26, 24, 0.85) 75%);
        border: 2px solid rgba(16, 185, 129, 0.6);
        border-radius: 20px;
        padding: 24px;
        margin: 18px 0;
        text-align: center;
    }
    .sporty-code-big {
        font-family: 'JetBrains Mono', monospace;
        font-size: 3.4rem;
        font-weight: 900;
        color: #10B981;
        letter-spacing: 0.15em;
        margin: 6px 0;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(15, 23, 42, 0.6);
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
    }
    .stTabs [aria-selected="true"] {
        color: #FFFFFF !important;
        background: rgba(255, 255, 255, 0.08) !important;
    }

    .stButton>button {
        background: linear-gradient(135deg, #0EA5E9 0%, #3B82F6 100%) !important;
        color: #FFFFFF !important;
        font-weight: 800 !important;
        border-radius: 14px !important;
        padding: 12px 24px !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

today_str = date.today().strftime("%Y-%m-%d")


def sync_pipeline(target_date=None):
    use_date = target_date or today_str
    fixtures, _ = fetcher.fetch_upcoming_fixtures(use_date, days_ahead=2)
    if not fixtures:
        return 0

    engine = FootballEngine()
    count = 0

    for m in fixtures:
        match_id = str(m["id"])
        utc_datetime_str = m.get("utcDate", "")
        m_date = utc_datetime_str[:10] if utc_datetime_str else use_date
        kickoff_time = utc_datetime_str[11:16] + " UTC" if len(utc_datetime_str) >= 16 else "18:45 UTC"

        h_team = m["homeTeam"]["name"]
        a_team = m["awayTeam"]["name"]

        custom = m.get("_custom_ratings", {})
        h_att = custom.get("h_att", 1.25)
        h_def = custom.get("h_def", 1.00)
        a_att = custom.get("a_att", 1.10)
        a_def = custom.get("a_def", 1.15)

        h_xg, a_xg = engine.calculate_xg(h_att, h_def, a_att, a_def)
        match_analysis = engine.predict_full_match(h_xg, a_xg, h_team, a_team)
        rec = match_analysis["recommendation"]

        score_data = m.get("score", {}).get("fullTime", {})
        h_goals = score_data.get("home")
        a_goals = score_data.get("away")
        status = m.get("status", "SCHEDULED")

        score_str = f"{h_goals} - {a_goals}" if (h_goals is not None and a_goals is not None) else "vs"

        boom_status = "PENDING"
        if status in ['FINISHED', 'FT'] and h_goals is not None and a_goals is not None:
            pick = rec["pick"]
            tot = h_goals + a_goals
            if "Home Win" in pick:
                boom_status = "BOOM" if h_goals > a_goals else "LOST"
            elif "Away Win" in pick:
                boom_status = "BOOM" if a_goals > h_goals else "LOST"
            elif "Home DNB" in pick:
                boom_status = "BOOM" if h_goals > a_goals else ("VOID" if h_goals == a_goals else "LOST")
            elif "Away DNB" in pick:
                boom_status = "BOOM" if a_goals > h_goals else ("VOID" if a_goals == h_goals else "LOST")
            elif "Home or Draw" in pick or "1X" in pick:
                boom_status = "BOOM" if h_goals >= a_goals else "LOST"
            elif "Draw or Away" in pick or "X2" in pick:
                boom_status = "BOOM" if a_goals >= h_goals else "LOST"
            elif "Over 2.5" in pick:
                boom_status = "BOOM" if tot > 2.5 else "LOST"
            elif "Under 3.5" in pick:
                boom_status = "BOOM" if tot < 3.5 else "LOST"
            else:
                boom_status = "BOOM" if tot >= 2 else "LOST"

        db.save_or_update_prediction({
            "match_date": m_date,
            "kickoff_time": kickoff_time,
            "match_id": match_id,
            "competition": "UEFA Conference League",
            "home_team": h_team,
            "away_team": a_team,
            "home_crest": "",
            "away_crest": "",
            "market_category": rec["category"],
            "market_pick": rec["pick"],
            "confidence": rec["prob"],
            "est_odds": rec["odds"],
            "tactical_tag": f"{h_xg:.2f} vs {a_xg:.2f} xG",
            "evidence_quality": "High-Yield",
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

    return count


sync_pipeline(today_str)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### 👑 Live Score & Engine Matrix")
    if st.button("⚡ Sync Live ESPN Scores & Results", use_container_width=True):
        count = sync_pipeline(today_str)
        st.success(f"Updated live scores for {count} fixtures!")
        st.rerun()

    st.markdown("---")
    st.caption("• **Live Feeds**: ESPN Real-Time Scoreboard (Zero Keys Needed)")
    st.caption("• **Markets**: Straight Wins, 1X/X2, DNB, Over/Under")

# ----------------- TOP BRAND HERO -----------------
st.markdown(f"""
<div class="hero-container">
    <div>
        <div class="brand-title">QUEEN RINS</div>
        <div style="font-size: 0.82rem; font-weight: 700; color: #38BDF8; letter-spacing: 0.05em; text-transform: uppercase;">
            Live ESPN Telemetry & Natural Odds Compounder
        </div>
    </div>
    <div class="status-capsule">
        <div class="radar-pulse"></div>
        <span>ESPN SCORES LIVE • {datetime.utcnow().strftime('%H:%M UTC')}</span>
    </div>
</div>
""", unsafe_allow_html=True)

daily_matches = db.get_predictions_filtered(exact_date=today_str)
perf = db.get_performance_metrics()

# ----------------- NAVIGATION TABS -----------------
main_tabs = st.tabs([
    "⚡ Daily Intelligence (Live Scores)",
    "🎯 ₦100 ➔ ₦70k Cashout Hunter",
    "📊 Model Performance"
])


def render_fixture_card(m):
    score_display = m["live_score"] if m["live_score"] != "vs" else "vs"
    is_live = m["match_status"] == 'LIVE'

    badge_html = (
        f'<span style="background: rgba(16, 185, 129, 0.2); color: #10B981; border: 1px solid #10B981; font-size: 0.76rem; font-weight: 800; padding: 4px 10px; border-radius: 8px;">WON (FT)</span>' if m["boom_status"] == 'BOOM' else (
            f'<span style="background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #EF4444; font-size: 0.76rem; font-weight: 800; padding: 4px 10px; border-radius: 8px;">LOST (FT)</span>' if m["boom_status"] == 'LOST' else (
                f'<span style="background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #EF4444; font-size: 0.76rem; font-weight: 800; padding: 4px 10px; border-radius: 8px;">🔴 LIVE {score_display}</span>' if is_live else
                f'<span class="comp-pill">🕒 {m.get("kickoff_time", "18:45 UTC")}</span>'
            )
        )
    )

    card_html = f"""
    <div class="match-deck-card">
        <div class="match-top-row">
            <span class="comp-pill">{m['competition']}</span>
            {badge_html}
        </div>
        <div class="versus-row">
            <span class="team-title">{m['home_team']}</span>
            <span class="vs-tag">{score_display}</span>
            <span class="team-title" style="text-align: right;">{m['away_team']}</span>
        </div>
        <div style="display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap;">
            <span style="background: rgba(255,255,255,0.04); color: #94A3B8; font-size: 0.72rem; font-weight: 700; padding: 3px 8px; border-radius: 6px;">{m.get('tactical_tag', '')}</span>
            <span style="background: rgba(139, 92, 246, 0.1); color: #C084FC; font-size: 0.72rem; font-weight: 700; padding: 3px 8px; border-radius: 6px;">{m['market_category']}</span>
        </div>
        <div class="prediction-capsule">
            <div>
                <div class="pick-label">Optimal Market Selection</div>
                <div class="pick-name">⚡ {m['market_pick']}</div>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <span class="prob-chip">{m['confidence']*100:.1f}% Model</span>
                <span class="odds-chip">@{m['est_odds']:.2f}</span>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


# TAB 1: DAILY INTELLIGENCE
with main_tabs[0]:
    st.caption("Live, accurate scores direct from ESPN with diverse Home Win, 1X, X2, and DNB selections.")
    cols = st.columns(2)
    for idx, item in enumerate(daily_matches):
        with cols[idx % 2]:
            render_fixture_card(item)

# TAB 2: CASHOUT HUNTER (SPORTYBET)
with main_tabs[1]:
    st.caption("🚀 Stacking Draw No Bet, Straight Wins, and Double Chance for massive ₦100-to-₦72k cashout multipliers.")

    cashout_tier = st.radio(
        "Select Multiplier Package:",
        ["10.00x Banker Slip", "35.00x Cashout Builder", "100.00x Mega Multi", "720.00x ₦100-to-₦72k Dream Slip"],
        horizontal=True
    )
    target_multiplier = {"10.00x Banker Slip": 10.0, "35.00x Cashout Builder": 35.0, "100.00x Mega Multi": 100.0, "720.00x ₦100-to-₦72k Dream Slip": 720.0}[cashout_tier]

    legs = []
    accum_odds = 1.0

    for r in daily_matches:
        accum_odds *= float(r["est_odds"])
        legs.append(r)
        if accum_odds >= target_multiplier:
            break

    accum_odds = round(accum_odds, 2)
    sample_stake = 100
    est_payout = f"₦{round(sample_stake * accum_odds):,}"

    col_btn, _ = st.columns([2, 1])
    with col_btn:
        if st.button("⚡ GENERATE SPORTYBET BOOKING CODE FOR THIS SLIP", use_container_width=True):
            if sportybet:
                with st.spinner("Connecting to SportyBet Server & Booking Ticket..."):
                    res = sportybet.generate_sportybet_code(legs)
                    if isinstance(res, tuple):
                        code = res[0]
                        err = res[1] if len(res) > 1 else None
                    else:
                        code = res
                        err = None

                    if code:
                        st.session_state["cashout_sporty_code"] = code
                        st.success(f"SportyBet Slip Booked! Code: {code}")
                    else:
                        st.error(f"SportyBet notice: {err or 'Could not complete booking'}")
            else:
                st.error("sportybet.py module missing.")

    if "cashout_sporty_code" in st.session_state:
        code = st.session_state["cashout_sporty_code"]
        st.markdown(f"""
        <div class="sporty-vault-card">
            <div style="font-size: 0.8rem; font-weight: 800; color: #10B981; letter-spacing: 0.1em; text-transform: uppercase;">
                Official SportyBet Booking Code ({cashout_tier})
            </div>
            <div class="sporty-code-big">{code}</div>
            <div style="color: #94A3B8; font-size: 0.88rem; font-weight: 600;">
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
                        {cashout_tier} ({len(legs)} Value Legs)
                    </span>
                    <div style="font-size: 1.6rem; font-weight: 900; color: #FFFFFF; margin-top: 4px;">Compound Odds: @{accum_odds:.2f}</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Projected Payout (₦{sample_stake:,} Stake)</div>
                    <div style="font-size: 1.8rem; font-weight: 900; color: #10B981;">{est_payout}</div>
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

# TAB 3: PERFORMANCE
with main_tabs[2]:
    st.caption("Empirical performance evaluation across settled matches.")
    if perf["market_breakdown"]:
        m_rows = [{"Market": k, "Settled": v["total"], "Won": v["won"], "Accuracy": f"{v['accuracy']}%"} for k, v in perf["market_breakdown"].items()]
        st.dataframe(pd.DataFrame(m_rows), hide_index=True, use_container_width=True)
    else:
        st.info("Settled matches update automatically via ESPN feeds.")
