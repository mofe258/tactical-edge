"""
db.py — Persistence Layer, Settlement Engine & Historical Verification
Handles SQLite transactions, prediction locking, live score settlement,
and auto-migrating schema repair.
"""

import sqlite3
import json
from datetime import datetime

DB_NAME = "predictions.db"


def get_connection():
    """Creates a thread-safe connection to SQLite."""
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes database with auto-migration.
    If an older incompatible table is detected, automatically upgrades it
    so index creation and queries never crash.
    """
    with get_connection() as conn:
        c = conn.cursor()

        # Inspect existing schema if table already exists
        c.execute("PRAGMA table_info(predictions)")
        existing_cols = {row["name"] for row in c.fetchall()}

        # If predictions table exists but lacks modern fields, drop old cache cleanly
        if existing_cols and ("match_status" not in existing_cols or "market_category" not in existing_cols):
            c.execute("DROP TABLE predictions")

        c.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_date TEXT NOT NULL,
                match_id TEXT UNIQUE NOT NULL,
                competition TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                market_category TEXT NOT NULL,
                market_pick TEXT NOT NULL,
                confidence REAL NOT NULL,
                est_odds REAL NOT NULL,
                locked_at TEXT NOT NULL,
                tactical_tag TEXT,
                match_status TEXT DEFAULT 'SCHEDULED',
                live_score TEXT DEFAULT 'vs',
                boom_status TEXT DEFAULT 'PENDING',
                full_time_home INTEGER,
                full_time_away INTEGER,
                prob_home REAL,
                prob_draw REAL,
                prob_away REAL,
                details_json TEXT DEFAULT '{}'
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                val TEXT NOT NULL
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS historical_settlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT UNIQUE,
                settled_at TEXT,
                prediction_correct INTEGER,
                brier_component REAL
            )
        ''')

        # Safely create indices
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_match_date ON predictions(match_date);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_status ON predictions(match_status);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_competition ON predictions(competition);")
        except sqlite3.OperationalError:
            pass

        conn.commit()


def save_or_update_prediction(match_data):
    """
    Saves predictions before kickoff.
    If the prediction is already locked, only updates match_status, scores,
    and settles results. The locked prediction is NEVER mutated mid-match.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM predictions WHERE match_id = ?", (match_data["match_id"],))
        existing = c.fetchone()

        if existing:
            c.execute("""
                UPDATE predictions
                SET match_status = ?,
                    live_score = ?,
                    boom_status = ?,
                    full_time_home = ?,
                    full_time_away = ?
                WHERE match_id = ?
            """, (
                match_data["match_status"],
                match_data["live_score"],
                match_data["boom_status"],
                match_data.get("full_time_home"),
                match_data.get("full_time_away"),
                match_data["match_id"]
            ))
        else:
            c.execute("""
                INSERT INTO predictions (
                    match_date, match_id, competition, home_team, away_team,
                    market_category, market_pick, confidence, est_odds,
                    locked_at, tactical_tag, match_status, live_score,
                    boom_status, full_time_home, full_time_away,
                    prob_home, prob_draw, prob_away, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_data["match_date"],
                match_data["match_id"],
                match_data["competition"],
                match_data["home_team"],
                match_data["away_team"],
                match_data["market_category"],
                match_data["market_pick"],
                match_data["confidence"],
                match_data["est_odds"],
                datetime.utcnow().strftime("%H:%M UTC"),
                match_data.get("tactical_tag", "Model Edge"),
                match_data.get("match_status", "SCHEDULED"),
                match_data.get("live_score", "vs"),
                match_data.get("boom_status", "PENDING"),
                match_data.get("full_time_home"),
                match_data.get("full_time_away"),
                match_data.get("prob_home", 0.33),
                match_data.get("prob_draw", 0.33),
                match_data.get("prob_away", 0.34),
                json.dumps(match_data.get("details", {}))
            ))
        conn.commit()


def get_predictions_filtered(min_date=None, competition=None, status=None, market_cat=None, search_query=None):
    """
    Retrieves predictions with multi-dimensional filtering.
    """
    with get_connection() as conn:
        c = conn.cursor()
        query = "SELECT * FROM predictions WHERE 1=1"
        params = []

        if min_date:
            query += " AND match_date >= ?"
            params.append(min_date)

        if competition and competition != "All Leagues":
            query += " AND competition = ?"
            params.append(competition)

        if status and status != "All Statuses":
            if status == "Live":
                query += " AND match_status IN ('IN_PLAY', 'PAUSED')"
            elif status == "Finished":
                query += " AND match_status IN ('FINISHED', 'FT')"
            elif status == "Upcoming":
                query += " AND match_status IN ('SCHEDULED', 'TIMED')"

        if market_cat and market_cat != "All Markets":
            query += " AND market_category = ?"
            params.append(market_cat)

        if search_query:
            query += " AND (home_team LIKE ? OR away_team LIKE ? OR competition LIKE ?)"
            term = f"%{search_query.strip()}%"
            params.extend([term, term, term])

        query += " ORDER BY match_date ASC, (confidence * est_odds) DESC"
        c.execute(query, params)
        return [dict(row) for row in c.fetchall()]


def get_performance_metrics():
    """
    Calculates empirical backtesting & calibration metrics.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT * FROM predictions
            WHERE match_status IN ('FINISHED', 'FT')
              AND boom_status IN ('BOOM', 'LOST')
            ORDER BY match_date DESC
        """)
        settled = [dict(r) for r in c.fetchall()]

    if not settled:
        return {
            "total_settled": 0,
            "won": 0,
            "lost": 0,
            "win_rate": 0.0,
            "brier_score": 0.0,
            "roi_1u": 0.0,
            "market_breakdown": {},
            "league_breakdown": {},
            "calibration_samples": []
        }

    total = len(settled)
    won = sum(1 for r in settled if r["boom_status"] == "BOOM")
    lost = total - won
    win_rate = round((won / total) * 100.0, 1)

    market_stats = {}
    league_stats = {}
    p_dists = []
    actuals = []
    total_returns = 0.0

    for r in settled:
        cat = r["market_category"]
        league = r["competition"]
        is_win = 1 if r["boom_status"] == "BOOM" else 0

        if is_win:
            total_returns += float(r["est_odds"])

        if cat not in market_stats:
            market_stats[cat] = {"total": 0, "won": 0}
        market_stats[cat]["total"] += 1
        market_stats[cat]["won"] += is_win

        if league not in league_stats:
            league_stats[league] = {"total": 0, "won": 0}
        league_stats[league]["total"] += 1
        league_stats[league]["won"] += is_win

        h_g = r.get("full_time_home")
        a_g = r.get("full_time_away")
        if h_g is not None and a_g is not None:
            actual = 0 if h_g > a_g else (1 if h_g == a_g else 2)
            p_dist = [
                float(r.get("prob_home") or 0.33),
                float(r.get("prob_draw") or 0.33),
                float(r.get("prob_away") or 0.34)
            ]
            p_dists.append(p_dist)
            actuals.append(actual)

    brier = 0.0
    if len(p_dists):
        from engine import FootballEngine
        brier = FootballEngine.calculate_brier_score(p_dists, actuals)

    total_staked = float(total)
    net_profit = total_returns - total_staked
    roi_pct = round((net_profit / total_staked) * 100.0, 1) if total_staked > 0 else 0.0

    for k in market_stats:
        t = market_stats[k]["total"]
        w = market_stats[k]["won"]
        market_stats[k]["accuracy"] = round((w / t) * 100.0, 1)

    for k in league_stats:
        t = league_stats[k]["total"]
        w = league_stats[k]["won"]
        league_stats[k]["accuracy"] = round((w / t) * 100.0, 1)

    conf_samples = [float(r["confidence"]) for r in settled]
    out_samples = [1 if r["boom_status"] == "BOOM" else 0 for r in settled]
    from engine import FootballEngine
    calibration = FootballEngine.compute_calibration_curve(conf_samples, out_samples)

    return {
        "total_settled": total,
        "won": won,
        "lost": lost,
        "win_rate": win_rate,
        "brier_score": brier,
        "roi_1u": roi_pct,
        "market_breakdown": market_stats,
        "league_breakdown": league_stats,
        "calibration_samples": calibration
    }


def set_setting(key, val):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, val) VALUES (?, ?)", (key, str(val)))
        conn.commit()


def get_setting(key, default=""):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT val FROM settings WHERE key = ?", (key,))
        row = c.fetchone()
        return row["val"] if row else default
