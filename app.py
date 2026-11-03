"""
app.py — TacticalEdge Platform
Minimalist Football Intelligence Dashboard with team crests, expandable
match analytics, transparent metric reporting, and verified data attribution.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
import json

import db
from engine import FootballEngine
import fetcher

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="TacticalEdge | Football Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

db.init_db()

# ----------------- REFINED MINIMALIST STYLING -----------------
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

    /* Top Bar */
    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 16px;
        margin-bottom: 20px;
        border-bottom: 1px solid #1A2234;
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
        font-size: 0.82rem;
        color: #64748B;
        margin-top: 2px;
    }

    /* KPI Summary Cards */
    .kpi-card {
        background: #101626;
        border: 1px solid #1A2234;
        border-radius: 10px;
        padding: 14px 18px;
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

    /* Refined Match Fixture Cards */
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
    .match-card-boom {
        background: #091A18 !important;
        border: 1px solid #10B981 !important;
    }
    .match-card-live {
        border: 1px solid #DC2626 !important;
    }

    /* Team Lineup Header */
    .team-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }
    .team-crest {
        width: 24px;
        height: 24px;
        object-fit: contain;
    }
    .team-name {
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF;
    }

    /* Badges */
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
    .badge-live {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .badge-boom {
        background: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    /* Model Selection Box */
    .pick-box {
        background: #0C1220;
        border: 1px solid #1A2234;
        border-radius: 8px;
        padding: 10px 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 10px;
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

    /* Tab styling */
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

# ----------------- SYNCHRONIZATION PIPELINE -----------------
def sync_pipeline():
    fixtures, err = fetcher.fetch_upcoming_fixtures(today_str, days_ahead=7)
    if err or not fixtures:
        return 0, err

    engine = FootballEngine()
    standings_cache = {}
    count = 0

    for m in fixtures:
        comp_code = m.get("competition", {}).get("code")
        if not comp_code:
            continue

        match_id = str(m["id"])
        m_date = m.get("utcDate", "")[:10]
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
        h_crest = m["homeTeam"].get("crest", "")
        a_crest = m["awayTeam"].get("crest", "")

        h_stat = team_stats.get(h_team, {"att_strength": 1.0, "def_strength": 1.0, "played": 10})
        a_stat = team_stats.get(a_team, {"att_strength": 1.0, "def_strength": 1.0, "played": 10})

        h_xg, a_xg = engine.calculate_xg(
            h_stat["att_strength"], h_stat["def_strength"],
            a_stat["att_strength"], a_stat["def_strength"]
        )

        match_analysis = engine.predict_full_match(h_xg, a_xg, h_team, a_team)
        rec = match_analysis["recommendation"]

        # Settlement check
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
            "match_id": match_id,
            "competition": m["competition"]["name"],
            "home_team": h_team,
            "away_team": a_team,
            "home_crest": h_crest,
            "away_crest": a_crest,
            "market_category": rec["category"],
            "market_pick": rec["pick"],
            "confidence": rec["prob"],
            "est_odds": rec["odds"],
            "tactical_tag": f"{h_xg:.2f} vs {a_xg:.2f} xG",
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


# Auto-sync on fresh arrival
existing_matches = db.get_predictions_filtered(min_date=today_str)
if not existing_matches and fetcher.get_api_key():
    with st.spinner("Connecting official API and compiling Bayesian models..."):
        sync_pipeline()
        existing_matches = db.get_predictions_filtered(min_date=today_str)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### Engine Controls")
    curr_key = fetcher.get_api_key()
    inp_key = st.text_input("Football-Data.org API Key", value=curr_key, type="password")
    if inp_key and inp_key != curr_key:
        db.set_setting("FOOTBALL_API_KEY", inp_key)
        st.success("API Key updated.")

    st.markdown("---")
    st.markdown("**Data Attribution**")
    st.caption("• Schedules & Standings: football-data.org v4")
    st.caption("• xG & Probabilities: Model-Derived (Dixon-Coles Bivariate)")
    last_sync = db.get_setting("last_successful_sync", "Never")
    st.caption(f"• Last Sync: {last_sync}")

    if st.button("Sync Match Schedule & Scores", use_container_width=True):
        count, err = sync_pipeline()
        if err:
            st.error(err)
        else:
            st.success(f"Synced {count} fixtures.")
            st.rerun()

# ----------------- HEADER & 4 KPI SUMMARY CARDS -----------------
last_sync_time = db.get_setting("last_successful_sync", "Awaiting Sync")
st.markdown(f"""
<div class="top-bar">
    <div>
        <div class="brand-title">⚡ TACTICALEDGE</div>
        <div class="brand-subtitle">Football Intelligence & Calibrated Prediction Platform</div>
    </div>
    <div style="font-size: 0.75rem; color: #64748B;">
        Data Freshness: {last_sync_time}
    </div>
</div>
""", unsafe_allow_html=True)

perf = db.get_performance_metrics()
today_count = len([m for m in existing_matches if m["match_date"] == today_str])
total_horizon_count = len(existing_matches)

k_cols = st.columns(4)
with k_cols[0]:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Fixtures Analysed</div>
        <div class="kpi-val">{total_horizon_count}</div>
        <div class="kpi-note">{today_count} scheduled for today</div>
    </div>
    """, unsafe_allow_html=True)

with k_cols[1]:
    settled_display = str(perf['total_settled']) if perf['total_settled'] > 0 else "0"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Settled Predictions</div>
        <div class="kpi-val">{settled_display}</div>
        <div class="kpi-note">{"Awaiting match completions" if perf['total_settled'] == 0 else f"{perf['won']} Won, {perf['lost']} Lost"}</div>
    </div>
    """, unsafe_allow_html=True)

with k_cols[2]:
    rate_color = "#10B981" if perf['win_rate_str'] != "N/A" else "#94A3B8"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Historical Accuracy</div>
        <div class="kpi-val" style="color: {rate_color};">{perf['win_rate_str']}</div>
        <div class="kpi-note">Calculated only on settled picks</div>
    </div>
    """, unsafe_allow_html=True)

with k_cols[3]:
    brier_val = perf['brier_score_str']
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Model Calibration (Brier)</div>
        <div class="kpi-val">{brier_val}</div>
        <div class="kpi-note">{"N/A (Requires N > 0 settled)" if brier_val == "N/A" else "Multi-class 1X2 scoring"}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ----------------- NAVIGATION TABS -----------------
main_tabs = st.tabs([
    "📊 Daily Intelligence",
    "👑 Elite Matches",
    "🎯 Accumulator Analysis",
    "📈 Model Performance",
    "🔍 Match Analytics",
    "ℹ️ Model Transparency"
])

def render_fixture_card(m, key_prefix):
    is_live = m["match_status"] in ['IN_PLAY', 'PAUSED']
    is_boom = m["boom_status"] == 'BOOM'
    cls = "match-card"
    if is_boom:
        cls += " match-card-boom"
    elif is_live:
        cls += " match-card-live"

    badge_html = (
        '<span class="badge-status badge-boom">✅ BOOM! WON</span>' if is_boom else (
            f'<span class="badge-status badge-live">🔴 LIVE &nbsp; {m["live_score"]}</span>' if is_live else (
                f'<span class="badge-status badge-scheduled">FT: {m["live_score"]}</span>' if m["match_status"] in ['FINISHED', 'FT'] else
                f'<span class="badge-status badge-scheduled">🗓️ {m["match_date"]}</span>'
            )
        )
    )

    h_crest_html = f'<img src="{m["home_crest"]}" class="team-crest"/>' if m.get("home_crest") else ''
    a_crest_html = f'<img src="{m["away_crest"]}" class="team-crest"/>' if m.get("away_crest") else ''

    card_html = f"""
    <div class="{cls}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 0.74rem; color: #64748B; font-weight: 600;">🏆 {m['competition']}</span>
            {badge_html}
        </div>
        <div class="team-row">
            {h_crest_html}
            <span class="team-name">{m['home_team']}</span>
            <span style="color: #64748B; font-weight: 400; font-size: 0.85rem; margin: 0 4px;">vs</span>
            {a_crest_html}
            <span class="team-name">{m['away_team']}</span>
        </div>
        <div style="display: flex; gap: 8px; margin-bottom: 10px;">
            <span style="font-size: 0.7rem; color: #64748B; background: #182238; padding: 2px 8px; border-radius: 4px;">{m['market_category']}</span>
            <span style="font-size: 0.7rem; color: #64748B; background: #182238; padding: 2px 8px; border-radius: 4px;">Expected Goals: {m.get('tactical_tag', 'Model-Derived')}</span>
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
    
    # Dedicated interactive Match Analytics expander
    with st.expander(f"View Analysis: {m['home_team']} vs {m['away_team']}"):
        details = json.loads(m.get("details_json", "{}"))
        if details:
            st.markdown(f"**Model Statistical Rationale:**")
            st.caption(details.get("explanation", "Grounded analysis compiled from league standings and attack/defense indices."))
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Home Expected Goals (xG)", f"{details.get('home_xg', 1.0):.2f}", help="Derived from Dixon-Coles bivariate distribution")
            with c2:
                st.metric("Away Expected Goals (xG)", f"{details.get('away_xg', 1.0):.2f}")
            with c3:
                p_h = details.get("prob_home", 0.33) * 100
                st.metric("Home Win Prob", f"{p_h:.1f}%")

            # Top 5 Scorelines
            scores = details.get("top_scores", [])
            if scores:
                st.markdown("**Top Probable Scorelines:**")
                score_str = " &nbsp;|&nbsp; ".join([f"**{s['score']}** ({s['prob']*100:.1f}%)" for s in scores])
                st.markdown(f"<span style='color: #94A3B8; font-size: 0.85rem;'>{score_str}</span>", unsafe_allow_html=True)
        else:
            st.info("Detailed statistical breakdown loading...")


# =============================================================================
# TAB 1: DAILY INTELLIGENCE
# =============================================================================
with main_tabs[0]:
    f1, f2, f3, f4 = st.columns([2, 1.5, 1.5, 1.5])
    with f1:
        search_term = st.text_input("Search teams or competitions", placeholder="e.g. Arsenal, Real Madrid, Premier League")
    with f2:
        leagues = ["All Leagues"] + sorted(list({r["competition"] for r in existing_matches}))
        sel_comp = st.selectbox("Competition Filter", leagues)
    with f3:
        sel_stat = st.selectbox("Match Status", ["All Statuses", "Upcoming", "Live", "Finished"])
    with f4:
        mkts = ["All Markets"] + sorted(list({r["market_category"] for r in existing_matches}))
        sel_mkt = st.selectbox("Market Filter", mkts)

    filtered = db.get_predictions_filtered(
        min_date=today_str,
        competition=sel_comp,
        status=sel_stat,
        market_cat=sel_mkt,
        search_query=search_term
    )

    if filtered:
        st.caption(f"Showing {len(filtered)} fixtures analysed by the predictive engine.")
        cols = st.columns(2)
        for idx, item in enumerate(filtered):
            with cols[idx % 2]:
                render_fixture_card(item, key_prefix=f"daily_{idx}")
    else:
        st.info("No fixtures found matching your active filter criteria.")

# =============================================================================
# TAB 2: ELITE MATCHES
# =============================================================================
with main_tabs[1]:
    st.caption("Curated fixtures featuring European powerhouses and English Premier League contenders.")
    ELITE_KW = [
        "manchester city", "arsenal", "liverpool", "chelsea", "tottenham", "manchester united",
        "real madrid", "barcelona", "atletico", "bayern", "dortmund", "leverkusen",
        "inter", "milan", "juventus", "napoli", "paris saint-germain", "psg", "sporting", "benfica"
    ]
    elite_matches = [
        r for r in existing_matches
        if any(k in f"{r['home_team']} {r['away_team']}".lower() for k in ELITE_KW)
        or r["competition"] in ["Premier League", "UEFA Champions League"]
    ]

    if elite_matches:
        cols_e = st.columns(2)
        for idx, item in enumerate(elite_matches):
            with cols_e[idx % 2]:
                render_fixture_card(item, key_prefix=f"elite_{idx}")
    else:
        st.info("No elite powerhouse fixtures scheduled in the current 7-day query horizon.")

# =============================================================================
# TAB 3: ACCUMULATOR ANALYSIS
# =============================================================================
with main_tabs[2]:
    st.caption("Mathematical multi-bet compounder stacking calibrated model selections to hit targeted ticket odds.")
    tier = st.radio("Target Compound Tier:", ["3.00x Odds", "5.00x Odds", "10.00x Odds", "15.00x Boom Slip", "50.00x Multi"], horizontal=True)
    t_val = {"3.00x Odds": 3.0, "5.00x Odds": 5.0, "10.00x Odds": 10.0, "15.00x Boom Slip": 14.5, "50.00x Multi": 50.0}[tier]

    legs = []
    accum_odds = 1.0

    for r in existing_matches:
        accum_odds *= float(r["est_odds"])
        legs.append(r)
        if accum_odds >= t_val:
            break

    accum_odds = round(accum_odds, 2)
    sample_stake = 2000
    est_ret = f"₦{round(sample_stake * accum_odds):,}"

    st.markdown(f"""
    <div style="background: #101626; border: 1px solid #1A2234; border-radius: 10px; padding: 18px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #1A2234; padding-bottom: 12px; margin-bottom: 12px; flex-wrap: wrap;">
            <div>
                <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">
                    {tier} Package ({len(legs)} Legs)
                </span>
                <div style="font-size: 1.35rem; font-weight: 800; color: #FFFFFF; margin-top: 4px;">Compound Odds: {accum_odds:.2f}</div>
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
                    <div style="font-size: 0.68rem; color: #64748B;">{leg['competition']} • {leg['match_date']}</div>
                    <div style="font-weight: 700; color: #FFFFFF; font-size: 0.9rem;">{leg['home_team']} vs {leg['away_team']}</div>
                    <div style="color: #38BDF8; font-weight: 700; font-size: 0.85rem; margin-top: 2px;">⚡ {leg['market_pick']}</div>
                </div>
                <div style="text-align: right;">
                    <span class="tag-prob">{leg['confidence']*100:.1f}%</span>
                    <div style="font-weight: 800; color: #F59E0B; font-size: 0.9rem; margin-top: 4px;">@{leg['est_odds']:.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# =============================================================================
# TAB 4: MODEL PERFORMANCE & CALIBRATION
# =============================================================================
with main_tabs[3]:
    st.caption("Empirical performance evaluation across completed, verified fixtures. Never deletes losing predictions.")

    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.markdown("##### Market-Specific Realized Accuracy")
        if perf["market_breakdown"]:
            m_rows = []
            for mkt, data in perf["market_breakdown"].items():
                m_rows.append({
                    "Market Category": mkt,
                    "Total Settled": data["total"],
                    "Correct": data["won"],
                    "Realized Hit Rate": f"{data['accuracy']}%"
                })
            st.dataframe(pd.DataFrame(m_rows), hide_index=True, use_container_width=True)
        else:
            st.info("Market accuracy statistics will populate here once upcoming matches reach full-time.")

    with p_col2:
        st.markdown("##### Empirical Calibration Reliability")
        if perf["calibration_samples"]:
            st.dataframe(pd.DataFrame(perf["calibration_samples"]), hide_index=True, use_container_width=True)
            st.caption("Demonstrates whether a predicted 70% model probability empirically hits ~70% of the time in sample.")
        else:
            st.info("Probability calibration bins calculate automatically when settled match sample size > 0.")

# =============================================================================
# TAB 5: MATCH ANALYTICS
# =============================================================================
with main_tabs[4]:
    st.caption("Interactive deep-dive into Dixon-Coles goal expectation matrices and market distributions.")

    if existing_matches:
        match_options = [f"{m['match_date']} | {m['home_team']} vs {m['away_team']} ({m['competition']})" for m in existing_matches]
        sel_idx = st.selectbox("Select Fixture for Deep Analysis:", range(len(match_options)), format_func=lambda i: match_options[i])
        selected_m = existing_matches[sel_idx]
        details = json.loads(selected_m.get("details_json", "{}"))

        if details:
            st.markdown(f"### {selected_m['home_team']} vs {selected_m['away_team']}")
            st.caption(f"🏆 {selected_m['competition']} • 🗓️ {selected_m['match_date']} • Status: {selected_m['match_status']}")

            st.info(f"**Grounded Statistical Rationale:**\n\n{details.get('explanation', '')}")

            d1, d2, d3 = st.columns(3)
            with d1:
                st.metric("Home Expected Goals (xG)", f"{details.get('home_xg', 1.0):.2f}", help="Derived from Dixon-Coles model with Bayesian shrinkage")
            with d2:
                st.metric("Away Expected Goals (xG)", f"{details.get('away_xg', 1.0):.2f}")
            with d3:
                st.metric("Model Prime Selection", f"{selected_m['market_pick']} (@{selected_m['est_odds']:.2f})")

            # 1X2 Probabilities Bar
            st.markdown("##### 1X2 Match Winner Probability Distribution")
            p_h = details.get("prob_home", 0.33) * 100
            p_d = details.get("prob_draw", 0.33) * 100
            p_a = details.get("prob_away", 0.34) * 100
            p_df = pd.DataFrame([{
                f"Home: {selected_m['home_team']}": f"{p_h:.1f}%",
                "Draw": f"{p_d:.1f}%",
                f"Away: {selected_m['away_team']}": f"{p_a:.1f}%"
            }])
            st.table(p_df)

            # Full Markets Table
            mkts = details.get("markets", {})
            if mkts:
                st.markdown("##### Comprehensive Market Pricing")
                m_list = []
                for cat, sub in mkts.items():
                    for name, vals in sub.items():
                        m_list.append({
                            "Category": cat,
                            "Selection": name,
                            "Model Probability": f"{vals['prob']*100:.1f}%",
                            "Fair Implied Odds": f"@{vals['odds']:.2f}"
                        })
                st.dataframe(pd.DataFrame(m_list), hide_index=True, use_container_width=True)
    else:
        st.info("No fixtures available for deep match analytics.")

# =============================================================================
# TAB 6: MODEL TRANSPARENCY
# =============================================================================
with main_tabs[5]:
    st.markdown("### Model Architecture & Transparency")
    st.markdown("""
    TacticalEdge produces mathematical football predictions grounded strictly in verifiable data.
    
    #### 1. Predictive Engine
    * **Algorithm:** Dixon-Coles Bivariate Poisson Goal Model with low-scoring correlation parameter ($\\tau$-adjustment for 0-0, 1-0, 0-1, and 1-1 scorelines).
    * **Rating Methodology:** Bayesian shrinkage regresses raw attacking and defensive ratings toward the league mean ($\mu = 1.0$) with prior weight $\\alpha = 6.0$ matches. This prevents small-sample distortions from producing extreme ($>90\%$) probabilities.
    * **Distribution Bounds:** All 1X2 probabilities are derived from an $8 \\times 8$ score matrix strictly normalized to $\sum P = 1.0$.

    #### 2. Data Sources & Attribution
    * **Schedules, Live Statuses & Standings:** Supplied via official API feeds from `football-data.org v4`.
    * **Expected Goals (xG) & Fair Odds:** Model-Derived by TacticalEdge. Bookmaker margins are estimated at $6.0\%$ to derive fair baseline odds.
    * **No Fabricated Statistics:** TacticalEdge never invents player injuries, referee stats, or unverified team news.

    #### 3. Model Limitations
    * Predictions reflect statistical strength based on completed league matches and goal rates. They do not account for unannounced tactical rotations or red cards during live matches.
    * Sports betting inherently involves variance. TacticalEdge calculates mathematical edges, not guaranteed outcomes.
    """)
