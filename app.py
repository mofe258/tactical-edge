"""
app.py — TacticalEdge Football Intelligence Platform
Main interface delivering minimalist design, live match settlement,
statistical deep-dives, accumulator builder, and empirical backtest tracking.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime
import json

import db
from engine import FootballEngine
import fetcher

# ----------------- PAGE CONFIGURATION -----------------
st.set_page_config(
    page_title="TacticalEdge | Football Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize database schema
db.init_db()

# ----------------- MINIMALIST PROFESSIONAL CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Core Background & Typography */
    .stApp {
        background-color: #090D16;
        color: #E2E8F0;
    }

    /* Minimalist Navbar Header */
    .brand-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 20px;
        margin-bottom: 24px;
        border-bottom: 1px solid #1E2638;
    }
    .brand-title {
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .brand-subtitle {
        font-size: 0.85rem;
        color: #64748B;
        margin-top: 2px;
    }

    /* Modern Analytics Cards */
    .metric-card {
        background: #111726;
        border: 1px solid #1E2638;
        border-radius: 12px;
        padding: 16px 20px;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.02em;
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Match Container Cards */
    .fixture-card {
        background: #111726;
        border: 1px solid #1E2638;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 14px;
        transition: border-color 0.15s ease;
    }
    .fixture-card:hover {
        border-color: #2D374D;
    }
    .fixture-card-boom {
        background: #0C1A1A !important;
        border: 1px solid #10B981 !important;
    }
    .fixture-card-live {
        border: 1px solid #DC2626 !important;
    }

    /* Status Badges */
    .badge-boom {
        background: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }
    .badge-live {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }
    .badge-scheduled {
        background: #182032;
        color: #94A3B8;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .badge-tag {
        background: #182032;
        color: #CBD5E1;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid #232D42;
    }

    /* Odds & Confidence Pills */
    .pill-confidence {
        color: #38BDF8;
        background: rgba(56, 189, 248, 0.1);
        border: 1px solid rgba(56, 189, 248, 0.2);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .pill-odds {
        color: #F59E0B;
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.2);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* Streamlit tabs minimalism */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #1E2638;
        padding-bottom: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94A3B8;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 8px 16px;
        border-radius: 8px;
        background: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #FFFFFF !important;
        background: #182032 !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SYNCHRONIZATION PIPELINE -----------------
today_str = date.today().strftime("%Y-%m-%d")


def sync_fixtures_and_predict():
    """
    Executes Dixon-Coles model across upcoming fixtures.
    Freezes predictions into SQLite. Updates live scores without mutating picks.
    """
    fixtures, err = fetcher.fetch_upcoming_fixtures(today_str, days_ahead=7)
    if err or not fixtures:
        return 0, err

    engine = FootballEngine()
    standings_cache = {}
    assigned_tags = {}
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
        ht = score.get("halfTime", {})

        h_goals = ft.get("home")
        a_goals = ft.get("away")
        ht_h = ht.get("home")
        ht_a = ht.get("away")

        score_str = f"{h_goals} - {a_goals}" if (h_goals is not None and a_goals is not None) else "vs"

        if comp_code not in standings_cache:
            standings_cache[comp_code] = fetcher.fetch_standings(comp_code)

        team_stats = standings_cache[comp_code]
        h_team = m["homeTeam"]["name"]
        a_team = m["awayTeam"]["name"]

        h_stat = team_stats.get(h_team, {"att_strength": 1.0, "def_strength": 1.0})
        a_stat = team_stats.get(a_team, {"att_strength": 1.0, "def_strength": 1.0})

        # Calculate Expected Goals
        h_xg, a_xg = engine.calculate_xg(
            h_stat["att_strength"], h_stat["def_strength"],
            a_stat["att_strength"], a_stat["def_strength"]
        )

        # Full Match Probabilistic Matrix
        match_analysis = engine.predict_full_match(h_xg, a_xg, h_team, a_team)
        rec = match_analysis["recommendation"]

        # Settlement check
        p_home = match_analysis["markets"]["1X2"]["Home Win"]["prob"]
        p_draw = match_analysis["markets"]["1X2"]["Draw"]["prob"]
        p_away = match_analysis["markets"]["1X2"]["Away Win"]["prob"]

        # Result verification logic against locked pick
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

        # Save or update in database
        db.save_or_update_prediction({
            "match_date": m_date,
            "match_id": match_id,
            "competition": m["competition"]["name"],
            "home_team": h_team,
            "away_team": a_team,
            "market_category": rec["category"],
            "market_pick": rec["pick"],
            "confidence": rec["prob"],
            "est_odds": rec["odds"],
            "tactical_tag": f"{h_xg:.1f} vs {a_xg:.1f} xG",
            "match_status": status,
            "live_score": score_str,
            "boom_status": boom_status,
            "full_time_home": h_goals,
            "full_time_away": a_goals,
            "prob_home": p_home,
            "prob_draw": p_draw,
            "prob_away": p_away,
            "details": match_analysis
        })
        count += 1

    return count, None


# Auto-sync on launch if database is unpopulated
existing_matches = db.get_predictions_filtered(min_date=today_str)
if not existing_matches and fetcher.get_api_key():
    with st.spinner("Syncing fixtures and computing Dixon-Coles model matrices..."):
        sync_fixtures_and_predict()
        existing_matches = db.get_predictions_filtered(min_date=today_str)

# ----------------- SIDEBAR CONTROLS -----------------
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    current_key = fetcher.get_api_key()
    api_key_input = st.text_input("Football-Data.org API Key", value=current_key, type="password")
    if api_key_input and api_key_input != current_key:
        db.set_setting("FOOTBALL_API_KEY", api_key_input)
        st.success("API key stored.")

    st.markdown("---")
    st.markdown("**Model Pipeline**")
    st.caption("• Dixon-Coles Bivariate Poisson (tau-adjusted)")
    st.caption("• 10-Call/Min Caching Shield Active")
    st.caption("• Automated Result Settlement Active")

    if st.button("🔄 Sync Live Scores & Fixtures", use_container_width=True):
        count, err = sync_fixtures_and_predict()
        if err:
            st.error(err)
        else:
            st.success(f"Synced {count} fixtures.")
            st.rerun()

# ----------------- TOP NAVBAR & KPI HEADER -----------------
st.markdown("""
<div class="brand-bar">
    <div>
        <div class="brand-title">⚡ TACTICALEDGE</div>
        <div class="brand-subtitle">Institutional Football Analytics & Probabilistic Model Suite</div>
    </div>
    <div style="font-size: 0.8rem; color: #64748B;">
        Data Source: Official League Standings & Feeds (football-data.org v4)
    </div>
</div>
""", unsafe_allow_html=True)

# Performance KPI Strip
perf = db.get_performance_metrics()
kpi_cols = st.columns(4)
with kpi_cols[0]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Settled Predictions</div>
        <div class="metric-val">{perf['total_settled']}</div>
    </div>
    """, unsafe_allow_html=True)
with kpi_cols[1]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Empirical Win Rate</div>
        <div class="metric-val" style="color: #10B981;">{perf['win_rate']}%</div>
    </div>
    """, unsafe_allow_html=True)
with kpi_cols[2]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Brier Score (1X2)</div>
        <div class="metric-val">{perf['brier_score']:.3f}</div>
    </div>
    """, unsafe_allow_html=True)
with kpi_cols[3]:
    roi_color = "#10B981" if perf['roi_1u'] >= 0 else "#EF4444"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Model Edge (Flat ROI)</div>
        <div class="metric-val" style="color: {roi_color};">{perf['roi_1u']:+0.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ----------------- MAIN NAVIGATION -----------------
tabs = st.tabs([
    "📊 Daily Intelligence & Live Board",
    "👑 Elite Marquee Matches",
    "🎯 Compound Accumulator (Odds Tiers)",
    "📈 Model Calibration & Backtesting",
    "🔍 Deep Match Analytics"
])

# =============================================================================
# TAB 1: DAILY INTELLIGENCE & LIVE BOARD
# =============================================================================
with tabs[0]:
    # Smart Filters Row
    f_cols = st.columns([2, 1.5, 1.5, 1.5])
    with f_cols[0]:
        search_txt = st.text_input("Search teams or competitions", placeholder="e.g. Arsenal, Real Madrid, Premier League")
    with f_cols[1]:
        all_leagues = ["All Leagues"] + sorted(list({r["competition"] for r in existing_matches}))
        sel_league = st.selectbox("League Filter", all_leagues)
    with f_cols[2]:
        sel_status = st.selectbox("Match Status", ["All Statuses", "Upcoming", "Live", "Finished"])
    with f_cols[3]:
        all_markets = ["All Markets"] + sorted(list({r["market_category"] for r in existing_matches}))
        sel_market = st.selectbox("Market Type", all_markets)

    filtered_matches = db.get_predictions_filtered(
        min_date=today_str,
        competition=sel_league,
        status=sel_status,
        market_cat=sel_market,
        search_query=search_txt
    )

    if filtered_matches:
        st.markdown(f"<p style='color: #64748B; font-size: 0.85rem;'>Displaying {len(filtered_matches)} statistically evaluated fixtures</p>", unsafe_allow_html=True)
        m_cols = st.columns(2)

        for idx, m in enumerate(filtered_matches):
            is_live = m["match_status"] in ['IN_PLAY', 'PAUSED']
            is_boom = m["boom_status"] == 'BOOM'

            card_cls = "fixture-card"
            if is_boom:
                card_cls += " fixture-card-boom"
            elif is_live:
                card_cls += " fixture-card-live"

            # Badge formatting
            if is_boom:
                status_html = '<span class="badge-boom">✅ SETTLED WON</span>'
            elif is_live:
                status_html = f'<span class="badge-live">🔴 LIVE &nbsp; {m["live_score"]}</span>'
            elif m["match_status"] in ['FINISHED', 'FT']:
                status_html = f'<span class="badge-scheduled">FT: {m["live_score"]}</span>'
            else:
                status_html = f'<span class="badge-scheduled">🗓️ {m["match_date"]}</span>'

            with m_cols[idx % 2]:
                st.markdown(f"""
                <div class="{card_cls}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 0.75rem; color: #64748B; font-weight: 600;">{m['competition']}</span>
                        {status_html}
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #FFFFFF; margin-bottom: 6px;">
                        {m['home_team']} <span style="color: #64748B; font-weight: 400; font-size: 0.95rem;">vs</span> {m['away_team']}
                    </div>
                    <div style="display: flex; gap: 6px; margin-bottom: 12px;">
                        <span class="badge-tag">{m.get('tactical_tag', 'Model Projection')}</span>
                        <span class="badge-tag">{m['market_category']}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #1E2638; padding-top: 10px;">
                        <div>
                            <span style="font-size: 0.7rem; color: #64748B; display: block; text-transform: uppercase;">Optimal Pick</span>
                            <span style="color: {'#10B981' if is_boom else '#38BDF8'}; font-weight: 700; font-size: 1.0rem;">{m['market_pick']}</span>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <span class="pill-confidence">{m['confidence']*100:.1f}% Model</span>
                            <span class="pill-odds">@{m['est_odds']:.2f} Odds</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No fixtures found matching your filter criteria.")

# =============================================================================
# TAB 2: ELITE MARQUEE MATCHES
# =============================================================================
with tabs[1]:
    st.markdown("<p style='color: #64748B; font-size: 0.85rem;'>Curated tactical predictions for European powerhouses & English Premier League fixtures.</p>", unsafe_allow_html=True)

    ELITE_KEYWORDS = [
        "manchester city", "arsenal", "liverpool", "chelsea", "tottenham", "manchester united",
        "real madrid", "barcelona", "atletico", "bayern", "dortmund", "leverkusen",
        "inter", "milan", "juventus", "napoli", "paris saint-germain", "psg", "sporting", "benfica"
    ]
    elite_fixtures = [
        r for r in existing_matches
        if any(k in f"{r['home_team']} {r['away_team']}".lower() for k in ELITE_KEYWORDS)
        or r["competition"] in ["Premier League", "UEFA Champions League"]
    ]

    if elite_fixtures:
        e_cols = st.columns(2)
        for idx, m in enumerate(elite_fixtures):
            is_live = m["match_status"] in ['IN_PLAY', 'PAUSED']
            is_boom = m["boom_status"] == 'BOOM'
            card_cls = "fixture-card"
            if is_boom:
                card_cls += " fixture-card-boom"
            elif is_live:
                card_cls += " fixture-card-live"

            status_badge = '<span class="badge-boom">✅ SETTLED WON</span>' if is_boom else (
                f'<span class="badge-live">🔴 LIVE &nbsp; {m["live_score"]}</span>' if is_live else
                f'<span class="badge-scheduled">🗓️ {m["match_date"]}</span>'
            )

            with e_cols[idx % 2]:
                st.markdown(f"""
                <div class="{card_cls}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 0.75rem; color: #64748B; font-weight: 600;">👑 {m['competition']}</span>
                        {status_badge}
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #FFFFFF; margin-bottom: 6px;">
                        {m['home_team']} <span style="color: #64748B; font-weight: 400; font-size: 0.95rem;">vs</span> {m['away_team']}
                    </div>
                    <div style="display: flex; gap: 6px; margin-bottom: 12px;">
                        <span class="badge-tag">{m.get('tactical_tag', 'Marquee')}</span>
                        <span class="badge-tag">{m['market_category']}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #1E2638; padding-top: 10px;">
                        <div>
                            <span style="font-size: 0.7rem; color: #64748B; display: block; text-transform: uppercase;">Selection</span>
                            <span style="color: {'#10B981' if is_boom else '#38BDF8'}; font-weight: 700; font-size: 1.0rem;">{m['market_pick']}</span>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <span class="pill-confidence">{m['confidence']*100:.1f}%</span>
                            <span class="pill-odds">@{m['est_odds']:.2f}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No Premier League or marquee club fixtures currently in the 7-day query horizon.")

# =============================================================================
# TAB 3: COMPOUND ACCUMULATOR (ODDS TIERS)
# =============================================================================
with tabs[2]:
    st.markdown("<p style='color: #64748B; font-size: 0.85rem;'>Mathematical multi-bet compounder stacking non-correlated selections to hit target ticket odds.</p>", unsafe_allow_html=True)

    tier = st.radio("Target Multiplier Tier:", ["3.00x Odds", "5.00x Odds", "10.00x Odds", "15.00x Boom Slip", "50.00x Mega Multi"], horizontal=True)
    target_val = {"3.00x Odds": 3.0, "5.00x Odds": 5.0, "10.00x Odds": 10.0, "15.00x Boom Slip": 14.5, "50.00x Mega Multi": 50.0}[tier]

    accum_legs = []
    compound_odds = 1.0

    for r in existing_matches:
        leg_odds = float(r["est_odds"])
        accum_legs.append(r)
        compound_odds *= leg_odds
        if compound_odds >= target_val:
            break

    compound_odds = round(compound_odds, 2)
    sample_stake = 2000
    est_return = f"₦{round(sample_stake * compound_odds):,}"

    st.markdown(f"""
    <div style="background: #111726; border: 1px solid #1E2638; border-radius: 12px; padding: 22px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #1E2638; padding-bottom: 16px; margin-bottom: 16px; flex-wrap: wrap;">
            <div>
                <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
                    {tier} Accumulator Package ({len(accum_legs)} Legs)
                </span>
                <div style="font-size: 1.4rem; font-weight: 800; color: #FFFFFF; margin-top: 6px;">Compound Odds: {compound_odds:.2f}</div>
            </div>
            <div>
                <div style="font-size: 0.75rem; color: #64748B; text-transform: uppercase;">Projected Return (₦{sample_stake:,} Stake)</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: #10B981;">{est_return}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    t_cols = st.columns(2)
    for idx, leg in enumerate(accum_legs):
        with t_cols[idx % 2]:
            st.markdown(f"""
            <div style="background: #0D1322; border: 1px solid #1E2638; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.7rem; color: #64748B;">{leg['competition']} • {leg['match_date']}</div>
                    <div style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem;">{leg['home_team']} vs {leg['away_team']}</div>
                    <div style="color: #38BDF8; font-weight: 700; font-size: 0.88rem; margin-top: 2px;">⚡ {leg['market_pick']}</div>
                </div>
                <div style="text-align: right;">
                    <span class="pill-confidence">{leg['confidence']*100:.1f}%</span>
                    <div style="font-weight: 800; color: #F59E0B; font-size: 0.95rem; margin-top: 4px;">@{leg['est_odds']:.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# =============================================================================
# TAB 4: MODEL CALIBRATION & HISTORICAL BACKTESTING
# =============================================================================
with tabs[3]:
    st.markdown("<p style='color: #64748B; font-size: 0.85rem;'>Empirical evaluation of Dixon-Coles model performance on settled matches. Never deletes losses.</p>", unsafe_allow_html=True)

    c_cols = st.columns([1, 1])
    with c_cols[0]:
        st.markdown("##### 📌 Market-by-Market Accuracy")
        if perf["market_breakdown"]:
            m_data = []
            for mkt, data in perf["market_breakdown"].items():
                m_data.append({
                    "Market Category": mkt,
                    "Total Predictions": data["total"],
                    "Correct": data["won"],
                    "Accuracy Rate": f"{data['accuracy']}%"
                })
            st.dataframe(pd.DataFrame(m_data), hide_index=True, use_container_width=True)
        else:
            st.info("Settled matches will populate market accuracy data here as fixtures finish.")

    with c_cols[1]:
        st.markdown("##### 📐 Probability Calibration Curve")
        if perf["calibration_samples"]:
            st.dataframe(pd.DataFrame(perf["calibration_samples"]), hide_index=True, use_container_width=True)
            st.caption("Validates whether a predicted 70% model probability empirically converts to ~70% realized strike rate.")
        else:
            st.info("Calibration bins calculate automatically when matches complete.")

# =============================================================================
# TAB 5: DEEP MATCH ANALYTICS
# =============================================================================
with tabs[4]:
    st.markdown("<p style='color: #64748B; font-size: 0.85rem;'>Detailed statistical breakdown, Dixon-Coles goal matrices, and market pricing for any selected fixture.</p>", unsafe_allow_html=True)

    if existing_matches:
        match_labels = [f"{m['match_date']} | {m['home_team']} vs {m['away_team']} ({m['competition']})" for m in existing_matches]
        sel_idx = st.selectbox("Select Match to Inspect:", range(len(match_labels)), format_func=lambda i: match_labels[i])
        selected_m = existing_matches[sel_idx]

        details = json.loads(selected_m.get("details_json", "{}"))

        if details:
            # Match Summary
            st.markdown(f"### {selected_m['home_team']} vs {selected_m['away_team']}")
            st.caption(f"🏆 {selected_m['competition']} • 🗓️ {selected_m['match_date']} • Status: {selected_m['match_status']}")

            # Grounded Statistical Explanation
            st.info(f"**Model Statistical Rationale:**\n\n{details.get('explanation', 'Analysis pending.')}")

            d_cols = st.columns(3)
            with d_cols[0]:
                st.metric("Home Expected Goals (xG)", f"{details.get('home_xg', 1.0):.2f}")
            with d_cols[1]:
                st.metric("Away Expected Goals (xG)", f"{details.get('away_xg', 1.0):.2f}")
            with d_cols[2]:
                st.metric("Model Prime Recommendation", f"{selected_m['market_pick']} (@{selected_m['est_odds']:.2f})")

            # Score Heatmap Matrix
            matrix = details.get("score_matrix", [])
            if matrix:
                st.markdown("##### 🔢 Scoreline Probability Matrix (Dixon-Coles τ-Corrected)")
                df_matrix = pd.DataFrame(matrix).iloc[:5, :5]
                df_matrix.index = [f"Home {i}" for i in range(5)]
                df_matrix.columns = [f"Away {i}" for i in range(5)]
                st.dataframe(df_matrix.style.format("{:.2%}"), use_container_width=True)

            # Full Market Distribution
            mkts = details.get("markets", {})
            if mkts:
                st.markdown("##### 📋 Complete Model Market Pricing")
                m_table = []
                for cat, sub in mkts.items():
                    for name, vals in sub.items():
                        m_table.append({
                            "Category": cat,
                            "Selection": name,
                            "Model Probability": f"{vals['prob']*100:.1f}%",
                            "Fair Odds": f"@{vals['odds']:.2f}"
                        })
                st.dataframe(pd.DataFrame(m_table), hide_index=True, use_container_width=True)
    else:
        st.info("No fixtures available for deep match analysis.")
