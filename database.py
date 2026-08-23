import sqlite3
from datetime import datetime

DB_FILE = "resume_analyzer.db"

def init_db():
    """Initializes the SQLite database and creates the analyses table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            resume_text TEXT NOT NULL,
            analysis_result TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_analysis(filename, resume_text, analysis_result):
    """Saves a resume analysis record to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO analyses (filename, timestamp, resume_text, analysis_result)
        VALUES (?, ?, ?, ?)
    """, (filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), resume_text, analysis_result))
    conn.commit()
    conn.close()

def get_all_analyses():
    """Retrieves all past analyses from the database, ordered by timestamp descending."""
    conn = sqlite3.connect(DB_FILE)
    # Configure connection to return rows as dictionary-like objects
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, timestamp, resume_text, analysis_result FROM analyses ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_analysis(analysis_id):
    """Deletes a specific analysis record from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    conn.commit()
    conn.close()
