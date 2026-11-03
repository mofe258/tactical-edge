import streamlit as st
import sqlite3
import json
from datetime import datetime, date
import numpy as np
from scipy.stats import poisson
import fetcher

st.set_page_config(
    page_title="Tactical Edge | SportyBet Multi-Market Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- DATABASE SETUP -----------------
DB_NAME = "predictions.db"
# Incrementing version auto-purges old generic records on first load
ENGINE_VERSION = "v7_full_sporty_diversity"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_date TEXT,
                    match_id TEXT UNIQUE,
                    competition TEXT,
                    home_team TEXT,
                    away_team TEXT,
                    market_category TEXT,
                    market_pick TEXT,
                    confidence REAL,
                    est_odds REAL,
                    locked_at TEXT,
                    extra_data TEXT DEFAULT '{}'
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, val TEXT)''')
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("SELECT val FROM settings WHERE key = ?", (key,))
        row = c.fetchone()
        return row[0] if row else default
    except sqlite3.OperationalError:
        return default
    finally:
        conn.close()

def set_setting(key, val):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, val) VALUES (?, ?)", (key, str(val)))
    conn.commit()
    conn.close()

def clear_all():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM predictions")
    conn.commit()
    conn.close()

def save_prediction(match_date, match_id, comp, home, away, category, pick, confidence, est_odds, extra_data="{}"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR REPLACE INTO predictions 
                     (match_date, match_id, competition, home_team, away_team, market_category, market_pick, confidence, est_odds, locked_at, extra_data)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (match_date, match_id, comp, home, away, category, pick, confidence, est_odds, datetime.utcnow().strftime("%H:%M UTC"), str(extra_data)))
        conn.commit()
    finally:
        conn.close()

def get_upcoming_predictions(start_date):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("""SELECT match_date, competition, home_team, away_team, market_category, market_pick, confidence, est_odds, locked_at, extra_data 
                     FROM predictions 
                     WHERE match_date >= ? 
                     ORDER BY match_date ASC, confidence DESC""", (start_date,))
        rows = c.fetchall()
        conn.close()
        return rows
    except sqlite3.OperationalError:
        c.execute("DROP TABLE IF EXISTS predictions")
        conn.commit()
        conn.close()
        init_db()
        return []

init_db()

# Auto-purge old single-market cache so new multi-market SportyBet picks load fresh
if get_setting("engine_version") != ENGINE_VERSION:
    clear_all()
    set_setting("engine_version", ENGINE_VERSION)

# ----------------- SPORTYBET MULTI-MARKET ENGINE -----------------
class SportyBetQuantEngine:
    def __init__(self, league_avg_home=1.45, league_avg_away=1.15):
        self.league_avg_home = league_avg_home
        self.league_avg_away = league_avg_away

    def calculate_xg(self, home_att, home_def, away_att, away_def):
        home_xg = max(0.2, home_att * away_def * self.league_avg_home)
        away_xg = max(0.2, away_att * home_def * self.league_avg_away)
        return home_xg, away_xg

    def evaluate_all_markets(self, home_xg, away_xg, home_team, away_team, max_goals=7):
        matrix = np.zeros((max_goals, max_goals))
        for h in range(max_goals):
            for a in range(max_goals):
                matrix[h][a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)

        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))
        dc_1x = prob_home + prob_draw
        dc_x2 = prob_away + prob_draw

        # Over / Under
        o05 = float(1.0 - matrix[0][0])
        o15 = float(1.0 - (matrix[0][0] + matrix[1][0] + matrix[0][1]))
        u45 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a <= 4]))

        # 1st Half Goals (First 45 min averages ~45% of total xG)
        exp_ht = 0.45 * (home_xg + away_xg)
        ht_o15 = float(1.0 - poisson.cdf(1, exp_ht))

        # Combos
        h_and_o15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h > a and (h + a >= 2)]))
        a_and_o15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if a > h and (h + a >= 2)]))
        h_and_o25 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h > a and (h + a >= 3)]))

        # Team Totals
        home_o25 = float(1.0 - sum(poisson.pmf(k, home_xg) for k in range(3)))

        # Handicaps
        away_hcap_3 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (h - a) < 3]))
        away_hcap_4 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (h - a) < 4]))

        # Catalog all candidate markets matching the winning tickets
        candidates = []

        # 1. Combos
        if h_and_o15 >= 0.58 and prob_home >= 0.65:
            candidates.append({"cat": "1X2 & Over/Under 1.5", "pick": "Home & Over 1.5", "prob": h_and_o15, "odds": 1.68})
        if a_and_o15 >= 0.55 and prob_away >= 0.60:
            candidates.append({"cat": "1X2 & Over/Under 1.5", "pick": "Away & Over 1.5", "prob": a_and_o15, "odds": 1.26})
        if h_and_o25 >= 0.52 and prob_home >= 0.68:
            candidates.append({"cat": "1X2 & Over/Under 2.5", "pick": "Home & Over 2.5", "prob": h_and_o25, "odds": 1.32})

        # 2. Handicaps
        if away_hcap_4 >= 0.94 and prob_home > 0.65:
            candidates.append({"cat": "Handicap 0:4", "pick": "Away (0:4)", "prob": away_hcap_4, "odds": 1.22})
        elif away_hcap_3 >= 0.90 and prob_home > 0.60:
            candidates.append({"cat": "Handicap 0:3", "pick": "Away (0:3)", "prob": away_hcap_3, "odds": 1.16})

        # 3. 1st Half Goals
        if ht_o15 >= 0.52 and (home_xg + away_xg) >= 3.2:
            candidates.append({"cat": "1st Half - Over/Under", "pick": "Over 1.5", "prob": ht_o15, "odds": 1.55})

        # 4. Team Totals
        if home_o25 >= 0.55 and home_xg >= 2.3:
            candidates.append({"cat": f"{home_team} Over/Under", "pick": "Over 2.5", "prob": home_o25, "odds": 1.29})

        # 5. Direct 1X2 / 1UP
        if prob_home >= 0.60 and prob_home <= 0.72:
            candidates.append({"cat": "1X2", "pick": "Home", "prob": prob_home, "odds": 1.77})
        elif prob_away >= 0.58 and prob_away <= 0.72:
            candidates.append({"cat": "1X2 - 1UP", "pick": "Away", "prob": prob_away, "odds": 1.34})

        # 6. Double Chance
        if prob_away > 0.50 and dc_x2 >= 0.85:
            candidates.append({"cat": "Double Chance - 1UP", "pick": "Draw or Away", "prob": dc_x2, "odds": 1.09})
        elif prob_home > 0.50 and dc_1x >= 0.88:
            candidates.append({"cat": "Double Chance - 1UP", "pick": "Home or Draw", "prob": dc_1x, "odds": 1.12})

        # 7. Safe Caps & Floors
        if u45 >= 0.88 and (home_xg + away_xg) < 2.8:
            candidates.append({"cat": "Over/Under", "pick": "Under 4.5", "prob": u45, "odds": 1.24})
        if o15 >= 0.85:
            candidates.append({"cat": "Over/Under", "pick": "Over 1.5", "prob": o15, "odds": 1.10})
        if o05 >= 0.95:
            candidates.append({"cat": "Over/Under", "pick": "Over 0.5", "prob": o05, "odds": 1.02})

        return candidates

# ----------------- LIQUID GLASS STYLES -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: radial-gradient(circle at 15% 20%, #0c1424 0%, #050811 100%); color: #e2e8f0; }

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
    .market-badge { display: inline-block; font-size: 0.72rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; text-transform: uppercase; margin-bottom: 6px; }
    .brand-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)

# ----------------- DATA PIPELINE -----------------
today_str = date.today().strftime("%Y-%m-%d")

def run_auto_sync():
    fixtures, err = fetcher.fetch_upcoming_fixtures(today_str, days_ahead=7)
    if err or not fixtures:
        return 0
    engine = SportyBetQuantEngine()
    standings_cache = {}
    
    # Market Diversity Tracker: Prevents any single bet from repeating more than twice
    category_counts = {}
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
        candidates = engine.evaluate_all_markets(h_xg, a_xg, h_team, a_team)

        if not candidates:
            continue

        # DIVERSITY ALLOCATION: Pick the highest confidence market that hasn't exceeded quota
        chosen = None
        for cand in candidates:
            cat_name = cand["cat"]
            # Allow at most 2 of the same category across the board
            if category_counts.get(cat_name, 0) < 2:
                chosen = cand
                category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
                break
        
        # Fallback to top candidate if all quotas hit
        if not chosen:
            chosen = candidates[0]

        save_prediction(
            m_date, str(m["id"]), m["competition"]["name"], 
            h_team, a_team, chosen["cat"], chosen["pick"], chosen["prob"], chosen["odds"]
        )
        count += 1
    return count

records = get_upcoming_predictions(today_str)

if not records and fetcher.API_KEY != "PASTE_YOUR_API_KEY_HERE":
    with st.spinner("⚡ Running SportyBet diversity engine across scheduled matches..."):
        run_auto_sync()
        records = get_upcoming_predictions(today_str)

# ----------------- MAIN INTERFACE -----------------
st.markdown('<div class="brand-title">Tactical Predictive Suite</div>', unsafe_allow_html=True)
st.markdown('<div style="color: #94a3b8; margin-bottom: 20px;">Modeled on authentic winning slips: Combos, Handicaps, 1st Half Goals, Team Totals & Double Chance.</div>', unsafe_allow_html=True)

if records:
    sorted_records = sorted(records, key=lambda x: x[6], reverse=True)

    main_tabs = st.tabs([
        "🔥 Odds Tier Accumulator (3, 5, 10, 20, 100)",
        "🎯 Sure Banger Hits (Lock-In Singles)",
        "🛡️ Sure Fixtures (Detailed Staking Signals)",
        "📊 All Daily Matches & Markets"
    ])

    # =========================================================================
    # TAB 1: ODDS TIER ACCUMULATOR BUILDER
    # =========================================================================
    with main_tabs[0]:
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Select your targeted odds tier. The engine automatically compounds high-conviction legs to match your desired slip.</p>", unsafe_allow_html=True)
        tier = st.radio("Choose Target Odds:", ["3 Odds", "5 Odds", "10 Odds", "20 Odds", "100 Odds"], horizontal=True)
        target_dict = {"3 Odds": 3.0, "5 Odds": 5.0, "10 Odds": 10.0, "20 Odds": 20.0, "100 Odds": 100.0}
        target_val = target_dict[tier]

        selected_legs = []
        current_odds = 1.0

        for r in sorted_records:
            leg_odds = r[7]
            selected_legs.append(r)
            current_odds *= leg_odds
            if current_odds >= target_val:
                break

        current_odds = round(current_odds, 2)
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
            m_date, m_comp, m_home, m_away, m_cat, m_pick, m_conf, m_odds = item[:8]
            with t_cols[idx % 2]:
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.7rem; color: #94a3b8;">{m_comp} &nbsp;•&nbsp; 🗓️ {m_date}</div>
                        <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">{m_home} vs {m_away}</div>
                        <div style="font-size: 0.68rem; color: #f87171; text-transform: uppercase; font-weight: 700; margin-top: 2px;">{m_cat}</div>
                        <div style="color: #38bdf8; font-weight: 800; font-size: 0.95rem;">👉 {m_pick}</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="tag-prob">{m_conf * 100:.1f}%</span>
                        <div style="font-weight: 800; color: #fbbf24; font-size: 1.05rem; margin-top: 4px;">@{m_odds:.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: SURE BANGER HITS
    # =========================================================================
    with main_tabs[1]:
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Dedicated to individual lock-in selections. Use these for heavy single stakes or conservative rollovers.</p>", unsafe_allow_html=True)
        bangers = sorted_records[:6]
        b_cols = st.columns(2)
        for idx, item in enumerate(bangers):
            m_date, m_comp, m_home, m_away, m_cat, m_pick, m_conf, m_odds = item[:8]
            with b_cols[idx % 2]:
                st.markdown(f"""
                <div class="glass-card" style="border-left: 4px solid #10b981;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 0.75rem; color: #94a3b8;">🏆 {m_comp}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">🗓️ {m_date}</span>
                    </div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #fff; margin-bottom: 8px;">
                        {m_home} <span style="color: #64748b; font-size: 1rem;">vs</span> {m_away}
                    </div>
                    <span class="market-badge">{m_cat}</span>
                    <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; padding: 10px 14px; margin-top: 6px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 0.65rem; color: #94a3b8; text-transform: uppercase;">🎯 BANGER SELECTION</div>
                            <div style="color: #34d399; font-weight: 800; font-size: 1.15rem;">{m_pick}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #fbbf24; font-weight: 800; font-size: 1.15rem;">@{m_odds:.2f}</div>
                            <div style="color: #38bdf8; font-weight: 700; font-size: 0.75rem;">{m_conf * 100:.1f}% Confidence</div>
                        </div>
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
            m_date, m_comp, m_home, m_away, m_cat, m_pick, m_conf, m_odds = item[:8]
            with s_cols[idx % 2]:
                st.markdown(f"""
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 0.75rem; color: #94a3b8;">🏆 {m_comp}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">🗓️ {m_date}</span>
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #fff; margin-bottom: 10px;">
                        {m_home} <span style="color: #64748b; font-weight: 400; font-size: 0.95rem;">vs</span> {m_away}
                    </div>
                    <span class="market-badge">{m_cat}</span>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px; margin-top: 8px;">
                        <div>
                            <span style="font-size: 0.68rem; color: #94a3b8; display: block;">RECOMMENDED BET</span>
                            <span style="color: #38bdf8; font-weight: 800; font-size: 1.1rem;">{m_pick}</span>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <span class="tag-prob">{m_conf * 100:.1f}%</span>
                            <span class="tag-odds">@{m_odds:.2f}</span>
                        </div>
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
            m_date, m_comp, m_home, m_away, m_cat, m_pick, m_conf, m_odds = item[:8]
            with cols_all[idx % 2]:
                st.markdown(f"""
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <span style="font-size: 0.75rem; color: #94a3b8;">{m_comp}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">🗓️ {m_date}</span>
                    </div>
                    <div style="font-weight: 700; color: #fff; font-size: 1.1rem; margin-bottom: 6px;">
                        {m_home} vs {m_away}
                    </div>
                    <span class="market-badge">{m_cat}</span>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px; margin-top: 6px;">
                        <span style="color: #34d399; font-weight: 800; font-size: 1rem;">{m_pick}</span>
                        <div>
                            <span class="tag-prob">{m_conf * 100:.1f}%</span>
                            <span class="tag-odds">@{m_odds:.2f}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

else:
    st.info("⚡ Analyzing upcoming matches and building diverse multi-market packages...")
