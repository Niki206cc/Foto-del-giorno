import os
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, jsonify

from .db import init_db, connect, get_settings, set_settings
from .mail_reader import sync_mail
from .ai_service import analyze_photo, test_ai_connection
from .publisher import send_to_postie
from .scheduler import start_scheduler, next_slot

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY", "cambia-questa-chiave")
init_db()
start_scheduler()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def index():
    with connect() as con:
        counts = {r["status"]: r["n"] for r in con.execute("SELECT status, count(*) n FROM photos GROUP BY status").fetchall()}
        rows = con.execute("""
            SELECT * FROM photos
            WHERE status IN ('new','processed','error')
            ORDER BY received_at DESC, id DESC
        """).fetchall()
    return render_template("index.html", rows=rows, counts=counts)

@app.get("/queue")
def queue():
    with connect() as con:
        rows = con.execute("""
            SELECT * FROM photos WHERE status='scheduled'
            ORDER BY scheduled_at ASC
        """).fetchall()
    return render_template("queue.html", rows=rows)

@app.get("/archive")
def archive():
    with connect() as con:
        rows = con.execute("""
            SELECT * FROM photos WHERE status IN ('sent','trash')
            ORDER BY COALESCE(published_at, updated_at) DESC LIMIT 500
        """).fetchall()
    return render_template("archive.html", rows=rows)

@app.route("/photo/<int:photo_id>", methods=["GET", "POST"])
def photo(photo_id):
    if request.method == "POST":
        fields = ["title","author","location","province","shot_date","article_text","instagram_text","alt_text","hashtags"]
        vals = [request.form.get(f, "") for f in fields]
        with connect() as con:
            con.execute(f"""
                UPDATE photos SET {", ".join(f"{f}=?" for f in fields)}, status='processed',
                updated_at=CURRENT_TIMESTAMP WHERE id=?
            """, (*vals, photo_id))
        flash("Modifiche salvate.", "success")
        return redirect(url_for("photo", photo_id=photo_id))

    with connect() as con:
        row = con.execute("SELECT * FROM photos WHERE id=?", (photo_id,)).fetchone()
    if not row:
        abort(404)
    return render_template("photo.html", row=row)

@app.get("/photo/<int:photo_id>/image")
def photo_image(photo_id):
    with connect() as con:
        row = con.execute("SELECT image_path FROM photos WHERE id=?", (photo_id,)).fetchone()
    if not row or not row["image_path"] or not Path(row["image_path"]).exists():
        abort(404)
    return send_file(row["image_path"])

@app.post("/photo/<int:photo_id>/ai")
def photo_ai(photo_id):
    with connect() as con:
        row = con.execute("SELECT * FROM photos WHERE id=?", (photo_id,)).fetchone()
    if not row:
        abort(404)
    try:
        result = analyze_photo(row)
        with connect() as con:
            con.execute("""
                UPDATE photos SET title=?, author=?, location=?, province=?, shot_date=?,
                article_text=?, instagram_text=?, alt_text=?, hashtags=?,
                status='processed', last_error=NULL, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (result["title"], result["author"], result["location"], result["province"],
                  result["shot_date"], result["article_text"], result["instagram_text"],
                  result["alt_text"], result["hashtags"], photo_id))
        flash("Foto elaborata con l'AI.", "success")
    except Exception as e:
        with connect() as con:
            con.execute("UPDATE photos SET status='error', last_error=? WHERE id=?", (str(e)[:1000], photo_id))
        flash(str(e), "danger")
    return redirect(url_for("photo", photo_id=photo_id))

@app.post("/photo/<int:photo_id>/schedule")
def photo_schedule(photo_id):
    raw = request.form.get("scheduled_at", "").strip()
    if raw:
        dt = datetime.fromisoformat(raw).astimezone()
    else:
        dt = next_slot()
    with connect() as con:
        con.execute("""
            UPDATE photos SET status='scheduled', scheduled_at=?, last_error=NULL,
            updated_at=CURRENT_TIMESTAMP WHERE id=?
        """, (dt.isoformat(), photo_id))
    flash(f"Programmata per {dt.strftime('%d/%m/%Y %H:%M')}.", "success")
    return redirect(url_for("queue"))

@app.post("/photo/<int:photo_id>/send")
def photo_send(photo_id):
    try:
        send_to_postie(photo_id)
        flash("Email inviata a Postie.", "success")
    except Exception as e:
        with connect() as con:
            con.execute("UPDATE photos SET status='error', last_error=? WHERE id=?", (str(e)[:1000], photo_id))
        flash(str(e), "danger")
    return redirect(url_for("photo", photo_id=photo_id))

@app.post("/photo/<int:photo_id>/trash")
def photo_trash(photo_id):
    with connect() as con:
        con.execute("UPDATE photos SET status='trash', updated_at=CURRENT_TIMESTAMP WHERE id=?", (photo_id,))
    flash("Foto spostata nel cestino.", "success")
    return redirect(url_for("index"))

@app.post("/sync")
def sync():
    try:
        result = sync_mail()
        flash(result["message"], "success" if result["ok"] else "warning")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("index"))

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        allowed = [
            "imap_host","imap_port","imap_ssl","imap_user","imap_password","imap_folder","imap_poll_minutes",
            "smtp_host","smtp_port","smtp_tls","smtp_user","smtp_password","smtp_from","postie_to",
            "postie_category","postie_tags","postie_status","publish_time","auto_schedule",
            "ai_provider","ai_api_key","ai_model","ai_prompt",
            "footer_text","photo_public_email","cleanup_published_days","cleanup_trash_days"
        ]
        current = get_settings()
        values = {}
        for k in allowed:
            if k in ("imap_ssl","smtp_tls","auto_schedule"):
                values[k] = "1" if request.form.get(k) else "0"
            elif k in ("imap_password","smtp_password","ai_api_key") and not request.form.get(k):
                values[k] = current.get(k, "")
            else:
                values[k] = request.form.get(k, "")
        set_settings(values)
        flash("Impostazioni salvate. Riavvia il container se cambi l'intervallo IMAP.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", s=get_settings())

@app.post("/settings/test-ai")
def settings_test_ai():
    try:
        message = test_ai_connection()
        flash(message, "success")
    except Exception as e:
        flash(f"Test AI fallito: {e}", "danger")
    return redirect(url_for("settings"))

@app.post("/maintenance/clear")
def maintenance_clear():
    mode = request.form.get("mode")
    with connect() as con:
        if mode == "trash":
            rows = con.execute("SELECT image_path FROM photos WHERE status='trash'").fetchall()
            for r in rows:
                if r["image_path"]:
                    Path(r["image_path"]).unlink(missing_ok=True)
            con.execute("DELETE FROM photos WHERE status='trash'")
            flash("Cestino svuotato.", "success")
        elif mode == "received":
            rows = con.execute("SELECT image_path FROM photos WHERE status IN ('new','processed','error')").fetchall()
            for r in rows:
                if r["image_path"]:
                    Path(r["image_path"]).unlink(missing_ok=True)
            con.execute("DELETE FROM photos WHERE status IN ('new','processed','error')")
            flash("Foto ricevute/non programmate eliminate.", "success")
        elif mode == "all":
            rows = con.execute("SELECT image_path FROM photos").fetchall()
            for r in rows:
                if r["image_path"]:
                    Path(r["image_path"]).unlink(missing_ok=True)
            con.execute("DELETE FROM photos")
            flash("Database Foto del giorno svuotato.", "success")
    return redirect(url_for("settings"))
