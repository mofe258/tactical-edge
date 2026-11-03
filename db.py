import sqlite3
from datetime import datetime

DB_NAME = "predictions.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Predictions Table
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
    # Settings Table (Remembers API Key & Preferences)
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    val TEXT
                )''')
    # Auto-repair missing columns
    for col, col_type in [("competition", "TEXT"), ("confidence", "REAL"), ("market", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE predictions ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

def save_prediction(match_date, match_id, comp, home, away, market, confidence):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR IGNORE INTO predictions 
                     (match_date, match_id, competition, home_team, away_team, market, confidence, locked_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (match_date, match_id, comp, home, away, market, confidence, datetime.utcnow().strftime("%H:%M UTC")))
        conn.commit()
    finally:
        conn.close()

def get_upcoming_predictions(start_date):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""SELECT match_date, competition, home_team, away_team, market, confidence, locked_at 
                 FROM predictions 
                 WHERE match_date >= ? 
                 ORDER BY match_date ASC, confidence DESC""", (start_date,))
    rows = c.fetchall()
    conn.close()
    return rows

def set_setting(key, val):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, val) VALUES (?, ?)", (key, str(val)))
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
