import os
import sqlite3
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'pdf_metadata.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS pdfs (
        id INTEGER PRIMARY KEY,
        filename TEXT,
        url TEXT,
        sha256 TEXT UNIQUE,
        title TEXT,
        sector TEXT,
        size INTEGER
    )
    ''')
    conn.commit()
    conn.close()

def insert_metadata(filename: str, url: str, sha256: str, title: str, sector: Optional[str], size: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO pdfs (filename, url, sha256, title, sector, size) VALUES (?, ?, ?, ?, ?, ?)',
                    (filename, url, sha256, title, sector or '', size))
        conn.commit()
    except sqlite3.IntegrityError:
        # duplicate sha256
        pass
    finally:
        conn.close()

def find_by_sha(sha256: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, filename, url, sha256, title, sector, size FROM pdfs WHERE sha256=?', (sha256,))
    row = cur.fetchone()
    conn.close()
    return row
