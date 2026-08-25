import sqlite3
from pathlib import Path

DB_PATH = Path("/app/data/database.db")

DEFAULT_SETTINGS = {
    "imap_host": "",
    "imap_port": "993",
    "imap_ssl": "1",
    "imap_user": "",
    "imap_password": "",
    "imap_folder": "INBOX",
    "imap_poll_minutes": "5",

    "smtp_host": "",
    "smtp_port": "587",
    "smtp_tls": "1",
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from": "",
    "postie_to": "",

    "postie_category": "La foto del giorno",
    "postie_category_id": "",
    "postie_tags": "",
    "postie_status": "publish",

    "publish_time": "12:30",
    "auto_schedule": "1",

    "ai_provider": "gemini",
    "ai_api_key": "",
    "ai_model": "gemini-2.5-flash",
    "ai_prompt": """Sei un redattore di Montagne & Paesi. Analizza la fotografia e la mail ricevuta.
Non inventare mai nomi di montagne, luoghi, persone o date non esplicitamente forniti.
Usa ciò che vedi solo per descrivere elementi visivi generici.
Individua sempre, se presente nella mail, il nome e cognome di chi ha scattato la foto e inseriscilo nel campo author.
Restituisci SOLO JSON valido con le chiavi:
title, author, location, province, shot_date, article_text, instagram_text, alt_text, hashtags.
article_text deve essere un breve testo giornalistico in italiano, naturale e non enfatico.""",

    "footer_text": """📸 Vuoi vedere anche la tua foto su Montagne & Paesi?

Inviala a {email_foto} indicando il luogo dello scatto e il tuo nome e cognome.

Potresti vederla pubblicata nella rubrica \"La foto del giorno\".""",
    "photo_public_email": "",
    "site_home_url": "https://www.montagneepaesi.com/",

    "cleanup_published_days": "90",
    "cleanup_trash_days": "30",
}

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            sender_email TEXT,
            sender_name TEXT,
            email_subject TEXT,
            email_body TEXT,
            received_at TEXT,

            image_path TEXT,
            image_name TEXT,
            image_hash TEXT,

            author TEXT,
            location TEXT,
            province TEXT,
            shot_date TEXT,

            title TEXT,
            article_text TEXT,
            instagram_text TEXT,
            alt_text TEXT,
            hashtags TEXT,

            status TEXT NOT NULL DEFAULT 'new',
            scheduled_at TEXT,
            published_at TEXT,
            sent_at TEXT,
            last_error TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_photos_status ON photos(status);
        CREATE INDEX IF NOT EXISTS idx_photos_scheduled_at ON photos(scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_photos_hash ON photos(image_hash);
        """)
        for k, v in DEFAULT_SETTINGS.items():
            con.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))

def get_settings():
    with connect() as con:
        rows = con.execute("SELECT key, value FROM settings").fetchall()
    data = DEFAULT_SETTINGS.copy()
    data.update({r["key"]: r["value"] for r in rows})
    return data

def set_settings(values):
    with connect() as con:
        for k, v in values.items():
            con.execute("""
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (k, str(v)))
