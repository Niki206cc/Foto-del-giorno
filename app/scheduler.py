from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from .db import connect, get_settings
from .mail_reader import sync_mail
from .publisher import send_to_postie

scheduler = BackgroundScheduler(timezone="Europe/Rome")

def next_slot():
    s = get_settings()
    hh, mm = [int(x) for x in (s.get("publish_time") or "12:30").split(":")]
    now = datetime.now().astimezone()
    candidate = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)

    with connect() as con:
        used = {
            r["day"] for r in con.execute("""
                SELECT substr(scheduled_at, 1, 10) AS day
                FROM photos WHERE status='scheduled' AND scheduled_at IS NOT NULL
            """).fetchall()
        }
    while candidate.date().isoformat() in used:
        candidate += timedelta(days=1)
    return candidate

def process_due():
    now = datetime.now().astimezone().isoformat()
    with connect() as con:
        rows = con.execute("""
            SELECT id FROM photos
            WHERE status='scheduled' AND scheduled_at <= ?
            ORDER BY scheduled_at ASC
        """, (now,)).fetchall()

    for r in rows:
        try:
            send_to_postie(r["id"])
        except Exception as e:
            with connect() as con:
                con.execute("""
                    UPDATE photos SET status='error', last_error=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """, (str(e)[:1000], r["id"]))

def poll_mail_job():
    try:
        sync_mail()
    except Exception:
        pass

def cleanup_job():
    s = get_settings()
    try:
        pub_days = int(s.get("cleanup_published_days") or 0)
    except ValueError:
        pub_days = 0
    try:
        trash_days = int(s.get("cleanup_trash_days") or 0)
    except ValueError:
        trash_days = 0

    now = datetime.now().astimezone()
    with connect() as con:
        rows = con.execute("SELECT id, image_path, status, published_at, updated_at FROM photos").fetchall()
        for row in rows:
            ref = row["published_at"] if row["status"] == "sent" else row["updated_at"]
            if not ref:
                continue
            try:
                dt = datetime.fromisoformat(ref)
                if dt.tzinfo is None:
                    dt = dt.astimezone()
            except Exception:
                continue
            age = (now - dt).days
            path = Path(row["image_path"]) if row["image_path"] else None

            if row["status"] == "sent" and pub_days > 0 and age >= pub_days:
                if path and path.exists():
                    path.unlink(missing_ok=True)
                con.execute("UPDATE photos SET image_path='' WHERE id=?", (row["id"],))

            if row["status"] == "trash" and trash_days > 0 and age >= trash_days:
                if path and path.exists():
                    path.unlink(missing_ok=True)
                con.execute("DELETE FROM photos WHERE id=?", (row["id"],))

def start_scheduler():
    if scheduler.running:
        return
    s = get_settings()
    try:
        mins = max(1, int(s.get("imap_poll_minutes") or 5))
    except ValueError:
        mins = 5
    scheduler.add_job(poll_mail_job, "interval", minutes=mins, id="imap", replace_existing=True, max_instances=1)
    scheduler.add_job(process_due, "interval", minutes=1, id="due", replace_existing=True, max_instances=1)
    scheduler.add_job(cleanup_job, "cron", hour=3, minute=30, id="cleanup", replace_existing=True, max_instances=1)
    scheduler.start()
