import sqlite3
import json
from datetime import datetime

DB_NAME = "predictions.db"


def execute_db(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
    except Exception:
        pass

    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
        if fetchone:
            res = cursor.fetchone()
            return dict(res) if res else None
        if fetchall:
            res = cursor.fetchall()
            return [dict(r) for r in res]
        return None
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")

        cursor.execute("PRAGMA table_info(predictions)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        if existing_cols and ("kickoff_time" not in existing_cols or "evidence_quality" not in existing_cols):
            cursor.execute("DROP TABLE IF EXISTS predictions")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_date TEXT NOT NULL,
                kickoff_time TEXT DEFAULT 'TBD',
                match_id TEXT UNIQUE NOT NULL,
                competition TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                home_crest TEXT DEFAULT '',
                away_crest TEXT DEFAULT '',
                market_category TEXT NOT NULL,
                market_pick TEXT NOT NULL,
                confidence REAL NOT NULL,
                est_odds REAL NOT NULL,
                locked_at TEXT NOT NULL,
                tactical_tag TEXT,
                evidence_quality TEXT DEFAULT 'Moderate Evidence',
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
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                val TEXT NOT NULL
            )
        """)

        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_date ON predictions(match_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON predictions(match_status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_competition ON predictions(competition);")
        except sqlite3.OperationalError:
            pass

        conn.commit()
    finally:
        cursor.close()
        conn.close()


def save_or_update_prediction(match_data):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM predictions WHERE match_id = ?", (match_data["match_id"],))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
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
            cursor.execute("""
                INSERT INTO predictions (
                    match_date, kickoff_time, match_id, competition, home_team, away_team,
                    home_crest, away_crest, market_category, market_pick,
                    confidence, est_odds, locked_at, tactical_tag, evidence_quality,
                    match_status, live_score, boom_status, full_time_home,
                    full_time_away, prob_home, prob_draw, prob_away, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_data["match_date"],
                match_data.get("kickoff_time", "TBD"),
                match_data["match_id"],
                match_data["competition"],
                match_data["home_team"],
                match_data["away_team"],
                match_data.get("home_crest", ""),
                match_data.get("away_crest", ""),
                match_data["market_category"],
                match_data["market_pick"],
                match_data["confidence"],
                match_data["est_odds"],
                datetime.utcnow().strftime("%H:%M UTC"),
                match_data.get("tactical_tag", "Model Edge"),
                match_data.get("evidence_quality", "Moderate Evidence"),
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
    finally:
        cursor.close()
        conn.close()


def get_predictions_filtered(min_date=None, competition=None, status=None, market_cat=None, search_query=None):
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
        elif status == "Postponed":
            query += " AND match_status IN ('POSTPONED', 'SUSPENDED', 'CANCELLED')"

    if market_cat and market_cat != "All Markets":
        query += " AND market_category = ?"
        params.append(market_cat)

    if search_query:
        query += " AND (home_team LIKE ? OR away_team LIKE ? OR competition LIKE ?)"
        term = f"%{search_query.strip()}%"
        params.extend([term, term, term])

    query += " ORDER BY match_date ASC, kickoff_time ASC, (confidence * est_odds) DESC"
    return execute_db(query, params, fetchall=True) or []


def get_performance_metrics():
    query = """
        SELECT * FROM predictions
        WHERE match_status IN ('FINISHED', 'FT')
          AND boom_status IN ('BOOM', 'LOST')
        ORDER BY match_date DESC
    """
    settled = execute_db(query, fetchall=True) or []

    if not settled:
        return {
            "total_settled": 0,
            "won": 0,
            "lost": 0,
            "win_rate_str": "N/A",
            "brier_score_str": "N/A",
            "roi_str": "N/A",
            "status_note": "Awaiting completed matches. Accuracy and Brier scores calculate automatically upon settlement.",
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

    brier = None
    if len(p_dists):
        try:
            from engine import FootballEngine
            brier = FootballEngine.calculate_brier_score(p_dists, actuals)
        except Exception:
            pass

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
    calibration = []
    try:
        from engine import FootballEngine
        calibration = FootballEngine.compute_calibration_curve(conf_samples, out_samples)
    except Exception:
        pass

    return {
        "total_settled": total,
        "won": won,
        "lost": lost,
        "win_rate_str": f"{win_rate}%",
        "brier_score_str": f"{brier:.3f}" if brier is not None else "N/A",
        "roi_str": f"{roi_pct:+0.1f}%",
        "status_note": f"Empirically verified across {total} settled fixture outcomes.",
        "market_breakdown": market_stats,
        "league_breakdown": league_stats,
        "calibration_samples": calibration
    }


def set_setting(key, val):
    execute_db("INSERT OR REPLACE INTO settings (key, val) VALUES (?, ?)", (key, str(val)), commit=True)


def get_setting(key, default=""):
    row = execute_db("SELECT val FROM settings WHERE key = ?", (key,), fetchone=True)
    return row["val"] if row else default
