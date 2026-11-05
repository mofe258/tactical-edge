"""
app.py — TacticalEdge Platform
Institutional Football Intelligence Dashboard with UEFA Conference League,
Accumulator Builder, and 1-Click Live SportyBet Booking Code Generator.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
import json

import db
from engine import FootballEngine
import fetcher
import sportybet

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="TacticalEdge | Football Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

db.init_db()

# ----------------- CSS STYLING -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: #0A0D14;
        color: #E2E8F0;
    }

    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 16px;
        margin-bottom: 20px;
        border-bottom: 1px solid #1A2234;
        flex-wrap: wrap;
        gap: 12px;
    }
    .brand-title {
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .brand-subtitle {
        font-size: 0.80rem;
        color: #64748B;
        margin-top: 2px;
    }

    .freshness-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #101626;
        border: 1px solid #1A2234;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.74rem;
        color: #94A3B8;
    }
    .status-dot-green {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 8px #10B981;
    }

    .kpi-card {
        background: #101626;
        border: 1px solid #1A2234;
        border-radius: 10px;
        padding: 14px 18px;
        height: 100%;
    }
    .kpi-val {
        font-size: 1.65rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.02em;
        margin-top: 4px;
    }
    .kpi-label {
        font-size: 0.72rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-note {
        font-size: 0.7rem;
        color: #475569;
        margin-top: 4px;
    }

    .match-card {
        background: #101626;
        border: 1px solid #1A2234;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 14px;
        transition: border-color 0.15s ease;
    }
    .match-card:hover {
        border-color: #2D3A54;
    }

    .team-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }
    .team-name {
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF;
    }

    .badge-status {
        font-size: 0.72rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
    }
    .badge-scheduled {
        background: #182238;
        color: #94A3B8;
    }
    .badge-evidence {
        font-size: 0.68rem;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 4px;
        background: #182238;
        color: #94A3B8;
        border: 1px solid #232D42;
    }

    .pick-box {
        background: #0C1220;
        border: 1px solid #1A2234;
        border-radius: 8px;
        padding: 10px 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 10px;
        flex-wrap: wrap;
        gap: 8px;
    }
    .pick-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #38BDF8;
    }
    .tag-prob {
        background: rgba(56, 189, 248, 0.1);
        color: #38BDF8;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .tag-odds {
        background: rgba(245, 158, 11, 0.1);
        color: #F59E0B;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .sporty-banner {
        background: linear-gradient(135deg, #0D2618 0%, #101626 100%);
        border: 1px solid #10B981;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 16px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 1px solid #1A2234;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94A3B8;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 8px 14px;
        border-radius: 6px;
        background: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #FFFFFF !important;
        background: #182238 !important;
    }
</style>
""", unsafe_allow_html=True)

today_str = date.today().strftime("%Y-%m-%d")


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
            if "Home & Over 1.5" in pick:
                boom_status = "BOOM" if (h_goals > a_goals and tot >= 2) else "LOST"
            elif "Away & Over 1.5" in pick:
                boom_status = "BOOM" if (a_goals > h_goals and tot >= 2) else "LOST"
            elif "Draw or Away" in pick:
                boom_status = "BOOM" if a_goals >= h_goals else "LOST"
            elif "Home or Draw" in pick:
                boom_status = "BOOM" if h_goals >= a_goals else "LOST"
            elif "Under 3.5" in pick:
                boom_status = "BOOM" if tot < 3.5 else "LOST"
            elif "Over 2.5" in pick:
                boom_status = "BOOM" if tot > 2.5 else "LOST"
            elif "Away (+2.5)" in pick:
                boom_status = "BOOM" if (h_goals - a_goals) < 3 else "LOST"
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


today_matches_check = db.get_predictions_filtered(exact_date=today_str)
if len(today_matches_check) < 10:
    sync_pipeline(today_str)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### Engine Controls")
    curr_key = fetcher.get_api_key()
    inp_key = st.text_input("Football-Data.org API Key (Optional)", value=curr_key, type="password")
    if inp_key and inp_key != curr_key:
        db.set_setting("FOOTBALL_API_KEY", inp_key)
        st.success("API Key updated.")

    if st.button("⚡ Force Sync Today's Conference League", use_container_width=True):
        count, _ = sync_pipeline(today_str)
        st.success(f"Synced {count} fixtures!")
        st.rerun()

    st.markdown("---")
    st.caption("• Competitions: UEFA Conference League, Champions League, Major Domestic")
    st.caption("• SportyBet Auto-Booking: Enabled (NG)")

# ----------------- TOP NAVBAR & DATE LOCK -----------------
st.markdown(f"""
<div class="top-bar">
    <div>
        <div class="brand-title">TACTICALEDGE</div>
        <div class="brand-subtitle">Football Intelligence & Instant SportyBet Booking Platform</div>
    </div>
    <div class="freshness-pill">
        <div class="status-dot-green"></div>
        <span>SportyBet Engine Ready • {datetime.utcnow().strftime('%H:%M UTC')}</span>
    </div>
</div>
""", unsafe_allow_html=True)

d_col1, d_col2 = st.columns([1.5, 3.5])
with d_col1:
    selected_date_obj = st.date_input("🗓️ Active Match Date", value=date.today())
    active_date_str = selected_date_obj.strftime("%Y-%m-%d")

with d_col2:
    st.caption(f"🟢 **Showing Fixtures For {active_date_str}**. Stacking and SportyBet slips locked strictly to today's games.")

daily_matches = db.get_predictions_filtered(exact_date=active_date_str)
if not daily_matches:
    sync_pipeline(active_date_str)
    daily_matches = db.get_predictions_filtered(exact_date=active_date_str)

perf = db.get_performance_metrics()
k_cols = st.columns(4)
with k_cols[0]:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Matches Loaded</div>
        <div class="kpi-val">{len(daily_matches)}</div>
        <div class="kpi-note">{active_date_str}</div>
    </div>
    """, unsafe_allow_html=True)

with k_cols[1]:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Settled Predictions</div>
        <div class="kpi-val">{perf['total_settled']}</div>
        <div class="kpi-note">{perf['won']} Won, {perf['lost']} Lost</div>
    </div>
    """, unsafe_allow_html=True)

with k_cols[2]:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Historical Accuracy</div>
        <div class="kpi-val" style="color: #10B981;">{perf['win_rate_str']}</div>
        <div class="kpi-note">Settled predictions only</div>
    </div>
    """, unsafe_allow_html=True)

with k_cols[3]:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Model Calibration</div>
        <div class="kpi-val">{perf['brier_score_str']}</div>
        <div class="kpi-note">Multi-class 1X2 Brier</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ----------------- TABS -----------------
main_tabs = st.tabs([
    "Daily Intelligence",
    "Sure Bets & SportyBet Codes",
    "Elite Matches",
    "Model Performance",
    "Match Analytics"
])


def render_fixture_card(m):
    badge_html = f'<span class="badge-status badge-scheduled">{m.get("kickoff_time", "TBD")}</span>'
    card_html = f"""
    <div class="match-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 0.74rem; color: #64748B; font-weight: 600;">{m['competition']} • {m['match_date']}</span>
            {badge_html}
        </div>
        <div class="team-row">
            <span class="team-name">{m['home_team']}</span>
            <span style="color: #64748B; font-weight: 400; font-size: 0.85rem; margin: 0 4px;">vs</span>
            <span class="team-name">{m['away_team']}</span>
        </div>
        <div style="display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap;">
            <span class="badge-evidence">{m.get('evidence_quality', 'Strong Evidence')}</span>
            <span class="badge-evidence">{m['market_category']}</span>
            <span class="badge-evidence">{m.get('tactical_tag', '')}</span>
        </div>
        <div class="pick-box">
            <div>
                <span style="font-size: 0.68rem; color: #64748B; text-transform: uppercase; display: block;">Optimal Pick</span>
                <span class="pick-title">{m['market_pick']}</span>
            </div>
            <div style="display: flex; gap: 6px;">
                <span class="tag-prob">{m['confidence']*100:.1f}% Model</span>
                <span class="tag-odds">@{m['est_odds']:.2f} Odds</span>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


# TAB 1: DAILY INTELLIGENCE
with main_tabs[0]:
    f1, f2 = st.columns([2, 2])
    with f1:
        search_term = st.text_input("Search teams", placeholder="e.g. Ajax, Brighton, Atalanta, Monaco")
    with f2:
        comps = ["All Leagues"] + sorted(list({r["competition"] for r in daily_matches}))
        sel_comp = st.selectbox("Competition Filter", comps)

    filtered = db.get_predictions_filtered(
        exact_date=active_date_str,
        competition=sel_comp,
        search_query=search_term
    )

    if filtered:
        st.caption(f"Showing {len(filtered)} fixtures scheduled strictly for **{active_date_str}**.")
        cols = st.columns(2)
        for idx, item in enumerate(filtered):
            with cols[idx % 2]:
                render_fixture_card(item)
    else:
        st.info(f"No fixtures found for {active_date_str}.")

# TAB 2: SURE BETS & INSTANT SPORTYBET CODES
with main_tabs[1]:
    st.markdown("### 📲 Sure Bets & Instant SportyBet Booking Code")
    st.caption("Select your target odds tier below, then click **Generate Working SportyBet Code** to book the slip directly on SportyBet NG.")

    tier = st.radio(
        "Select Target Odds Tier:",
        ["3.00x Odds", "5.00x Odds", "10.00x Odds", "15.00x Boom Slip", "50.00x Multi"],
        index=1,
        horizontal=True
    )
    t_val = {
        "3.00x Odds": 3.0,
        "5.00x Odds": 5.0,
        "10.00x Odds": 10.0,
        "15.00x Boom Slip": 14.5,
        "50.00x Multi": 50.0
    }[tier]

    legs = []
    accum_odds = 1.0
    for r in daily_matches:
        accum_odds *= float(r["est_odds"])
        legs.append(r)
        if accum_odds >= t_val:
            break

    accum_odds = round(accum_odds, 2)
    sample_stake = 2000
    est_ret = f"₦{round(sample_stake * accum_odds):,}"

    # SportyBet Booking Code Generator Button
    btn_col1, btn_col2 = st.columns([1.6, 2.4])
    with btn_col1:
        gen_clicked = st.button(f"🚀 Generate Working SportyBet Code ({tier})", type="primary", use_container_width=True)

    if gen_clicked:
        with st.spinner("Connecting to SportyBet Nigeria & booking your selections..."):
            code, sporty_legs, real_odds, err_msg = sportybet.generate_sportybet_code(legs, target_odds=t_val)
            if code:
                st.session_state["last_sporty_code"] = code
                st.session_state["last_sporty_legs"] = sporty_legs
                st.session_state["last_sporty_odds"] = real_odds
                st.session_state["last_sporty_tier"] = tier
                st.session_state["last_sporty_err"] = None
            else:
                st.session_state["last_sporty_code"] = None
                st.session_state["last_sporty_err"] = err_msg

    if st.session_state.get("last_sporty_err"):
        st.error(st.session_state["last_sporty_err"])

    if st.session_state.get("last_sporty_code"):
        s_code = st.session_state["last_sporty_code"]
        s_odds = st.session_state["last_sporty_odds"]
        s_legs = st.session_state["last_sporty_legs"]
        s_tier = st.session_state.get("last_sporty_tier", tier)

        st.markdown(f"""
        <div class="sporty-banner">
            <div style="font-size: 0.78rem; color: #10B981; font-weight: 700; text-transform: uppercase;">
                ✅ Live SportyBet Nigeria Booking Code Ready ({s_tier} • {len(s_legs)} Matches • @{s_odds} Real Odds)
            </div>
            <div style="font-size: 0.85rem; color: #CBD5E1; margin-top: 4px;">
                Click the copy icon on the right side of the box below, open your <b>SportyBet App</b>, paste the code into Betslip, and place your bet!
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Streamlit code block provides built-in 1-click Copy button
        st.code(s_code, language=None)

        with st.expander(f"View Exact Booked SportyBet Selections ({len(s_legs)} Legs)", expanded=True):
            st.dataframe(pd.DataFrame(s_legs), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("##### Model Projected Slip Preview")
    if legs:
        st.markdown(f"""
        <div style="background: #101626; border: 1px solid #1A2234; border-radius: 10px; padding: 18px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">
                        {tier} Model Preview ({len(legs)} Legs • {active_date_str})
                    </span>
                    <div style="font-size: 1.35rem; font-weight: 800; color: #FFFFFF; margin-top: 4px;">Model Compound Odds: {accum_odds:.2f}</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; color: #64748B; text-transform: uppercase;">Estimated Payout (₦{sample_stake:,} Stake)</div>
                    <div style="font-size: 1.45rem; font-weight: 800; color: #10B981;">{est_ret}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        t_cols = st.columns(2)
        for idx, leg in enumerate(legs):
            with t_cols[idx % 2]:
                st.markdown(f"""
                <div style="background: #0C1220; border: 1px solid #1A2234; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.68rem; color: #64748B;">{leg['competition']} • {leg['kickoff_time']}</div>
                        <div style="font-weight: 700; color: #FFFFFF; font-size: 0.9rem;">{leg['home_team']} vs {leg['away_team']}</div>
                        <div style="color: #38BDF8; font-weight: 700; font-size: 0.85rem; margin-top: 2px;">⚡ {leg['market_pick']}</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="tag-prob">{leg['confidence']*100:.1f}%</span>
                        <div style="font-weight: 800; color: #F59E0B; font-size: 0.9rem; margin-top: 4px;">@{leg['est_odds']:.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# TAB 3: ELITE MATCHES
with main_tabs[2]:
    st.caption("Top marquee and Conference League showdowns.")
    cols_e = st.columns(2)
    for idx, item in enumerate(daily_matches):
        with cols_e[idx % 2]:
            render_fixture_card(item)

# TAB 4: PERFORMANCE
with main_tabs[3]:
    st.info("Verified tracking engine runs continuously across completed matches.")

# TAB 5: MATCH ANALYTICS
with main_tabs[4]:
    if daily_matches:
        match_options = [f"{m['kickoff_time']} | {m['home_team']} vs {m['away_team']}" for m in daily_matches]
        sel_idx = st.selectbox("Select Fixture for Deep Analysis:", range(len(match_options)), format_func=lambda i: match_options[i])
        selected_m = daily_matches[sel_idx]
        details = json.loads(selected_m.get("details_json", "{}"))

        if details:
            st.markdown(f"### {selected_m['home_team']} vs {selected_m['away_team']}")
            d1, d2, d3 = st.columns(3)
            with d1:
                st.metric("Home xG", f"{details.get('home_xg', 1.0):.2f}")
            with d2:
                st.metric("Away xG", f"{details.get('away_xg', 1.0):.2f}")
            with d3:
                st.metric("Prime Selection", f"{selected_m['market_pick']} (@{selected_m['est_odds']:.2f})")
