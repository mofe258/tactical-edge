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
                    locked_at TEXT
                )''')
    conn.commit()
    conn.close()

def save_prediction(match_date, match_id, comp, home, away, market, confidence):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO predictions 
                     (match_date, match_id, competition, home_team, away_team, market, confidence, locked_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (match_date, match_id, comp, home, away, market, confidence, datetime.utcnow().strftime("%H:%M UTC")))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Already locked, do not modify
    finally:
        conn.close()

def get_predictions(match_date):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT competition, home_team, away_team, market, confidence, locked_at FROM predictions WHERE match_date = ?", (match_date,))
    rows = c.fetchall()
    conn.close()
    return rows