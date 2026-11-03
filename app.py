import streamlit as st
import sqlite3
import json
from datetime import datetime, date
import numpy as np
from scipy.stats import poisson
import fetcher

st.set_page_config(
    page_title="Tactical Edge | SportyBet Quant Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- DATABASE CONFIG & AUTO-PURGE -----------------
DB_NAME = "predictions.db"
# Incrementing version auto-purges old cache on reload
ENGINE_VERSION = "v11_sportybet_true_blueprint"

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
                    tactical_tag TEXT,
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

def save_prediction(match_date, match_id, comp, home, away, category, pick, confidence, est_odds, tactical_tag, extra_data="{}"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR REPLACE INTO predictions 
                     (match_date, match_id, competition, home_team, away_team, market_category, market_pick, confidence, est_odds, locked_at, tactical_tag, extra_data)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (match_date, match_id, comp, home, away, category, pick, confidence, est_odds, datetime.utcnow().strftime("%H:%M UTC"), tactical_tag, str(extra_data)))
        conn.commit()
    finally:
        conn.close()

def get_upcoming_predictions(start_date):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("""SELECT match_date, competition, home_team, away_team, market_category, market_pick, confidence, est_odds, locked_at, tactical_tag, extra_data 
                     FROM predictions 
                     WHERE match_date >= ? 
                     ORDER BY (confidence * est_odds) DESC""", (start_date,))
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

# Auto-wipe cache when engine version updates
if get_setting("engine_version") != ENGINE_VERSION:
    clear_all()
    set_setting("engine_version", ENGINE_VERSION)

# ----------------- SPORTYBET BLUEPRINT ENGINE -----------------
class SportyBetBlueprintEngine:
    def __init__(self, league_avg_home=1.45, league_avg_away=1.15):
        self.league_avg_home = league_avg_home
        self.league_avg_away = league_avg_away

    def calculate_xg(self, home_att, home_def, away_att, away_def):
        home_xg = max(0.4, home_att * away_def * self.league_avg_home)
        away_xg = max(0.3, away_att * home_def * self.league_avg_away)
        return home_xg, away_xg

    def assign_tactical_market(self, home_xg, away_xg, home_team, away_team, assigned_categories, max_goals=7):
        matrix = np.zeros((max_goals, max_goals))
        for h in range(max_goals):
            for a in range(max_goals):
                matrix[h][a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)

        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))

        dc_1x = prob_home + prob_draw
        dc_x2 = prob_away + prob_draw

        # Goal metrics
        total_xg = home_xg + away_xg
        h_and_o15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h > a and (h + a >= 2)]))
        a_and_o15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if a > h and (h + a >= 2)]))
        h_and_o25 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h > a and (h + a >= 3)]))

        # 1st Half Goals (~45% of total match xG)
        exp_ht = 0.45 * total_xg
        ht_o15 = float(1.0 - poisson.cdf(1, exp_ht))

        # Team Totals
        home_o25 = float(1.0 - sum(poisson.pmf(k, home_xg) for k in range(3)))

        # Handicaps
        away_hcap_3 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (h - a) < 3]))
        away_hcap_4 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (h - a) < 4]))
        u45 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a <= 4]))

        # Candidates matched directly to winning slips
        candidates = []

        # 1. 1st Half Blitz (e.g. PSG v Slovan @ 1.55)
        if total_xg >= 3.2 and ht_o15 >= 0.50 and assigned_categories.get("1ST_HALF", 0) < 1:
            candidates.append({"cat": "1st Half - Over/Under", "pick": "Over 1.5", "prob": ht_o15, "odds": 1.55, "tag": "⚡ 1st Half Blitz", "key": "1ST_HALF"})

        # 2. Team Over 2.5 (e.g. Barcelona Over 2.5 @ 1.29)
        if home_xg >= 2.3 and home_o25 >= 0.52 and assigned_categories.get("TEAM_TOTAL", 0) < 1:
            candidates.append({"cat": f"{home_team} Over/Under", "pick": "Over 2.5", "prob": home_o25, "odds": 1.29, "tag": "👑 Elite Home Giant", "key": "TEAM_TOTAL"})

        # 3. Combo: Home & Over 1.5 (e.g. Chelsea v Leeds @ 1.68)
        if prob_home >= 0.65 and h_and_o15 >= 0.55 and assigned_categories.get("HOME_COMBO", 0) < 2:
            candidates.append({"cat": "1X2 & Over/Under 1.5", "pick": "Home & Over 1.5", "prob": h_and_o15, "odds": 1.68, "tag": "🔥 Home Attack Dominance", "key": "HOME_COMBO"})

        # 4. Combo: Away & Over 1.5 (e.g. Benfica @ 1.26)
        if prob_away >= 0.60 and a_and_o15 >= 0.52 and assigned_categories.get("AWAY_COMBO", 0) < 2:
            candidates.append({"cat": "1X2 & Over/Under 1.5", "pick": "Away & Over 1.5", "prob": a_and_o15, "odds": 1.26, "tag": "🚗 Dominant Away Trip", "key": "AWAY_COMBO"})

        # 5. Combo: Home & Over 2.5 (e.g. Al Nassr @ 1.32)
        if prob_home >= 0.68 and h_and_o25 >= 0.50 and assigned_categories.get("HOME_COMBO_25", 0) < 1:
            candidates.append({"cat": "1X2 & Over/Under 2.5", "pick": "Home & Over 2.5", "prob": h_and_o25, "odds": 1.32, "tag": "⚽ High-Scoring Home Win", "key": "HOME_COMBO_25"})

        # 6. Handicap 0:3 / 0:4 (e.g. Galatasaray +3 @ 1.16, Viking FK +4 @ 1.22)
        if prob_home >= 0.62 and away_hcap_4 >= 0.94 and assigned_categories.get("HANDICAP", 0) < 2:
            candidates.append({"cat": "Handicap 0:4", "pick": "Away (0:4)", "prob": away_hcap_4, "odds": 1.22, "tag": "🎯 Deep Handicap Cushion", "key": "HANDICAP"})
        elif prob_home >= 0.58 and away_hcap_3 >= 0.88 and assigned_categories.get("HANDICAP", 0) < 2:
            candidates.append({"cat": "Handicap 0:3", "pick": "Away (0:3)", "prob": away_hcap_3, "odds": 1.16, "tag": "🎯 +3 Goal Safety Buffer", "key": "HANDICAP"})

        # 7. Double Chance 1UP (e.g. Celtic @ 1.09)
        if prob_away >= 0.48 and dc_x2 >= 0.82 and assigned_categories.get("DC", 0) < 2:
            candidates.append({"cat": "Double Chance - 1UP", "pick": "Draw or Away", "prob": dc_x2, "odds": 1.09, "tag": "🛡️ Away Safety Insurance", "key": "DC"})
        elif prob_home >= 0.52 and dc_1x >= 0.85 and assigned_categories.get("DC", 0) < 2:
            candidates.append({"cat": "Double Chance - 1UP", "pick": "Home or Draw", "prob": dc_1x, "odds": 1.12, "tag": "🛡️ Home Safety Insurance", "key": "DC"})

        # 8. High Defensive Ceiling: Under 4.5 (e.g. Liverpool v Atletico @ 1.24 - Strictly max 1 per board)
        if total_xg < 2.8 and u45 >= 0.86 and assigned_categories.get("UNDER_45", 0) < 1:
            candidates.append({"cat": "Over/Under", "pick": "Under 4.5", "prob": u45, "odds": 1.24, "tag": "🔒 Tactical Defense Cap", "key": "UNDER_45"})

        # 9. Direct Match Winner (e.g. Cruz Azul @ 1.77, Arsenal @ 1.34)
        if 0.58 <= prob_home <= 0.72 and assigned_categories.get("1X2", 0) < 2:
            candidates.append({"cat": "1X2", "pick": "Home", "prob": prob_home, "odds": 1.77, "tag": "🏆 Resolute Home Winner", "key": "1X2"})
        elif 0.55 <= prob_away <= 0.72 and assigned_categories.get("1X2", 0) < 2:
            candidates.append({"cat": "1X2 - 1UP", "pick": "Away", "prob": prob_away, "odds": 1.34, "tag": "🚀 Decisive Away Win", "key": "1X2"})

        # Fallback if specific profile slots are filled
        if not candidates:
            if dc_x2 >= dc_1x:
                candidates.append({"cat": "Double Chance - 1UP", "pick": "Draw or Away", "prob": dc_x2, "odds": 1.18, "tag": "🛡️ Double Chance Cushion", "key": "DC"})
            else:
                candidates.append({"cat": "Double Chance - 1UP", "pick": "Home or Draw", "prob": dc_1x, "odds": 1.18, "tag": "🛡️ Double Chance Cushion", "key": "DC"})

        # Sort by expected value to pick the best match-specific bet
        candidates.sort(key=lambda x: (x["prob"] * x["odds"]), reverse=True)
        chosen = candidates[0]
        assigned_categories[chosen["key"]] = assigned_categories.get(chosen["key"], 0) + 1
        return chosen

# ----------------- UI STYLING -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: radial-gradient(circle at 15% 20%, #0c1424 0%, #050811 100%); color: #e2e8f0; }

    .ticket-hero {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.14) 0%, rgba(16, 185, 129, 0.08) 100%);
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
    .tactical-pill { display: inline-block; font-size: 0.72rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; margin-bottom: 6px; }
    .market-badge { display: inline-block; font-size: 0.72rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; text-transform: uppercase; margin-bottom: 6px; margin-left: 6px; }
    .brand-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)

# ----------------- DATA PIPELINE -----------------
today_str = date.today().strftime("%Y-%m-%d")

def run_auto_sync():
    fixtures, err = fetcher.fetch_upcoming_fixtures(today_str, days_ahead=7)
    if err or not fixtures:
        return 0
    engine = SportyBetBlueprintEngine()
    standings_cache = {}
    assigned_categories = {}
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
        res = engine.assign_tactical_market(h_xg, a_xg, h_team, a_team, assigned_categories)

        save_prediction(
            m_date, str(m["id"]), m["competition"]["name"], 
            h_team, a_team, res["cat"], res["pick"], res["prob"], res["odds"], res["tag"]
        )
        count += 1
    return count

records = get_upcoming_predictions(today_str)

if not records and fetcher.API_KEY != "PASTE_YOUR_API_KEY_HERE":
    with st.spinner("⚡ Assembling authentic SportyBet multi-market slips..."):
        run_auto_sync()
        records = get_upcoming_predictions(today_str)

# ----------------- MAIN INTERFACE -----------------
st.markdown('<div class="brand-title">Tactical Predictive Suite</div>', unsafe_allow_html=True)
st.markdown('<div style="color: #94a3b8; margin-bottom: 20px;">Modeled directly on winning accumulator slips: Combos, Handicaps, 1st Half Goals, Team Totals & Double Chance.</div>', unsafe_allow_html=True)

if records:
    main_tabs = st.tabs([
        "🔥 Odds Tier Accumulator (3, 5, 10, 14–20, 100)",
        "🎯 Sure Banger Hits (Lock-In Singles)",
        "🛡️ Sure Fixtures (Detailed Staking Signals)",
        "📊 All Daily Matches & Markets"
    ])

    # =========================================================================
    # TAB 1: ODDS TIER ACCUMULATOR BUILDER
    # =========================================================================
    with main_tabs[0]:
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Select your target odds tier. The engine stacks varied tactical legs directly mirroring your winning slips.</p>", unsafe_allow_html=True)
        tier = st.radio("Choose Target Odds:", ["3 Odds", "5 Odds", "10 Odds", "14–20 Odds (Boom Slip)", "100 Odds"], horizontal=True)
        target_dict = {"3 Odds": 3.0, "5 Odds": 5.0, "10 Odds": 10.0, "14–20 Odds (Boom Slip)": 14.32, "100 Odds": 100.0}
        target_val = target_dict[tier]

        selected_legs = []
        current_odds = 1.0

        for r in records:
            leg_odds = r[7]
            selected_legs.append(r)
            current_odds *= leg_odds
            if current_odds >= target_val:
                break

        current_odds = round(current_odds, 2)
        rec_stakes = {"3 Odds": 10000, "5 Odds": 5000, "10 Odds": 2000, "14–20 Odds (Boom Slip)": 2000, "100 Odds": 500}
        stake = rec_stakes[tier]
        est_return = f"₦{round(stake * current_odds):,}"

        st.markdown(f"""
        <div class="ticket-hero">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; border-bottom: 1px dashed rgba(255,255,255,0.15); padding-bottom: 16px; margin-bottom: 20px;">
                <div>
                    <span style="background: #ef4444; color: #fff; padding: 4px 12px; border-radius: 50px; font-weight: 800; font-size: 0.75rem; text-transform: uppercase;">
                        🔥 {tier} Multi-Bet Package ({len(selected_legs)} Fold)
                    </span>
                    <div style="font-size: 1.6rem; font-weight: 800; color: #fff; margin-top: 8px;">Compound Multi-Market Slip</div>
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
                📋 Matches on this Ticket:
            </div>
        """, unsafe_allow_html=True)

        t_cols = st.columns(2)
        for idx, item in enumerate(selected_legs):
            m_date, m_comp, m_home, m_away, m_cat, m_pick, m_conf, m_odds, m_lock, m_tag = item[:10]
            with t_cols[idx % 2]:
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.7rem; color: #94a3b8;">{m_comp} &nbsp;•&nbsp; 🗓️ {m_date}</div>
                        <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">{m_home} vs {m_away}</div>
                        <div style="margin-top: 4px;">
                            <span class="tactical-pill">{m_tag}</span>
                            <span class="market-badge">{m_cat}</span>
                        </div>
                        <div style="color: #38bdf8; font-weight: 800; font-size: 1rem; margin-top: 2px;">👉 {m_pick}</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="tag-prob">{m_conf * 100:.1f}%</span>
                        <div style="font-weight: 800; color: #fbbf24; font-size: 1.1rem; margin-top: 4px;">@{m_odds:.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: SURE BANGER HITS
    # =========================================================================
    with main_tabs[1]:
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Dedicated to high-confidence single lock-ins (Combos, Handicaps & Double Chance).</p>", unsafe_allow_html=True)
        bangers = records[:6]
        b_cols = st.columns(2)
        for idx, item in enumerate(bangers):
            m_date, m_comp, m_home, m_away, m_cat, m_pick, m_conf, m_odds, m_lock, m_tag = item[:10]
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
                    <span class="tactical-pill">{m_tag}</span>
                    <span class="market-badge">{m_cat}</span>
                    <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; padding: 12px 14px; margin-top: 8px; display: flex; justify-content: space-between; align-items: center;">
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
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Detailed cards specifying the tactical matchup and the exact market to stake.</p>", unsafe_allow_html=True)
        s_cols = st.columns(2)
        for idx, item in enumerate(records[:10]):
            m_date, m_comp, m_home, m_away, m_cat, m_pick, m_conf, m_odds, m_lock, m_tag = item[:10]
            with s_cols[idx % 2]:
                st.markdown(f"""
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 0.75rem; color: #94a3b8;">🏆 {m_comp}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">🗓️ {m_date}</span>
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #fff; margin-bottom: 8px;">
                        {m_home} <span style="color: #64748b; font-weight: 400; font-size: 0.95rem;">vs</span> {m_away}
                    </div>
                    <span class="tactical-pill">{m_tag}</span>
                    <span class="market-badge">{m_cat}</span>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px; margin-top: 8px;">
                        <div>
                            <span style="font-size: 0.68rem; color: #94a3b8; display: block;">RECOMMENDED BET</span>
                            <span style="color: #38bdf8; font-weight: 800; font-size: 1.1rem;">👉 {m_pick}</span>
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
        filtered = records
        if search_query:
            filtered = [r for r in records if search_query.lower() in f"{r[2]} {r[3]} {r[1]}".lower()]
        cols_all = st.columns(2)
        for idx, item in enumerate(filtered):
            m_date, m_comp, m_home, m_away, m_cat, m_pick, m_conf, m_odds, m_lock, m_tag = item[:10]
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
                    <span class="tactical-pill">{m_tag}</span>
                    <span class="market-badge">{m_cat}</span>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px; margin-top: 6px;">
                        <span style="color: #34d399; font-weight: 800; font-size: 1rem;">👉 {m_pick}</span>
                        <div>
                            <span class="tag-prob">{m_conf * 100:.1f}%</span>
                            <span class="tag-odds">@{m_odds:.2f}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

else:
    st.info("⚡ Analyzing matches and generating SportyBet multi-market slips...")
