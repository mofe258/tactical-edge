import sqlite3
from datetime import datetime

DB_NAME = "predictions.db"

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
                    market TEXT,
                    confidence REAL,
                    locked_at TEXT,
                    extra_markets TEXT DEFAULT '{}'
                )''')
    conn.commit()
    conn.close()

def save_prediction(match_date, match_id, comp, home, away, market, confidence, extra_markets="{}"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR REPLACE INTO predictions 
                     (match_date, match_id, competition, home_team, away_team, market, confidence, locked_at, extra_markets)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (match_date, match_id, comp, home, away, market, confidence, datetime.utcnow().strftime("%H:%M UTC"), str(extra_markets)))
        conn.commit()
    finally:
        conn.close()

def get_upcoming_predictions(start_date):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("""SELECT match_date, competition, home_team, away_team, market, confidence, locked_at, extra_markets 
                     FROM predictions 
                     WHERE match_date >= ? 
                     ORDER BY match_date ASC, confidence DESC""", (start_date,))
        rows = c.fetchall()
        conn.close()
        return rows
    except sqlite3.OperationalError:
        # Auto-heal: If an old database schema exists, reset it cleanly
        c.execute("DROP TABLE IF EXISTS predictions")
        conn.commit()
        conn.close()
        init_db()
        return []

def clear_all():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM predictions")
    conn.commit()
    conn.close()
