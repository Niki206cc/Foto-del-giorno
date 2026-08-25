import email
import hashlib
import imaplib
import re
from email.header import decode_header, make_header
from pathlib import Path
from datetime import datetime
from .db import connect, get_settings

PHOTO_DIR = Path("/app/data/photos")
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def decode(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return str(value)


def extract_sender(msg):
    candidates = [msg.get("From"), msg.get("Reply-To"), msg.get("Sender"), msg.get("Return-Path")]
    for raw in candidates:
        if not raw:
            continue
        decoded = decode(raw).strip()
        for name, addr in email.utils.getaddresses([decoded]):
            if addr:
                return decode(name).strip(), addr.strip()
    return "", ""


def extract_text(msg):
    candidates = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = (part.get("Content-Disposition") or "").lower()
            if ctype in ("text/plain", "text/html") and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                    if ctype == "text/html":
                        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
                        text = re.sub(r"<[^>]+>", " ", text)
                    candidates.append(text)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            candidates.append(payload.decode(charset, errors="replace"))
    return "\n".join(candidates).strip()


def _already_imported(message_id):
    with connect() as con:
        row = con.execute(
            "SELECT 1 FROM photos WHERE message_id=? OR message_id LIKE ? LIMIT 1",
            (message_id, message_id + "#%"),
        ).fetchone()
    return row is not None


def _image_part_info(part):
    """Riconosce immagini anche quando Elementor/Post SMTP usa MIME generico."""
    ctype = (part.get_content_type() or "").lower()
    filename = decode(part.get_filename()).strip()
    ext = Path(filename).suffix.lower() if filename else ""

    if ctype in ALLOWED_TYPES:
        fallback_ext = ALLOWED_TYPES[ctype]
        return filename or f"foto{fallback_ext}", fallback_ext

    # Alcuni invii WordPress/Elementor arrivano come application/octet-stream
    # pur avendo un filename .jpg/.jpeg/.png/.webp corretto.
    if ext in ALLOWED_EXTENSIONS:
        normalized_ext = ".jpg" if ext == ".jpeg" else ext
        return filename, normalized_ext

    return None, None


def sync_mail():
    s = get_settings()
    if not s["imap_host"] or not s["imap_user"] or not s["imap_password"]:
        return {"ok": False, "message": "IMAP non configurato", "added": 0}

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    port = int(s.get("imap_port") or 993)
    client = imaplib.IMAP4_SSL(s["imap_host"], port) if s.get("imap_ssl") == "1" else imaplib.IMAP4(s["imap_host"], port)
    client.login(s["imap_user"], s["imap_password"])
    typ, _ = client.select(s.get("imap_folder") or "INBOX")
    if typ != "OK":
        client.logout()
        return {"ok": False, "message": "Impossibile aprire la cartella IMAP", "added": 0}

    typ, data = client.search(None, "ALL")
    if typ != "OK":
        client.logout()
        return {"ok": False, "message": "Errore ricerca IMAP", "added": 0}

    added = 0
    deleted = 0
    skipped = 0

    for seq in data[0].split():
        typ, raw = client.fetch(seq, "(RFC822)")
        if typ != "OK" or not raw or not isinstance(raw[0], tuple):
            continue

        msg = email.message_from_bytes(raw[0][1])
        message_id = (msg.get("Message-ID") or f"imap-{seq.decode()}").strip()

        if _already_imported(message_id):
            client.store(seq, "+FLAGS", "\\Deleted")
            deleted += 1
            continue

        subject = decode(msg.get("Subject"))
        sender_name, sender_email = extract_sender(msg)
        body = extract_text(msg)
        received = msg.get("Date", "")
        try:
            received_iso = email.utils.parsedate_to_datetime(received).isoformat()
        except Exception:
            received_iso = datetime.now().astimezone().isoformat()

        images = []
        for part in msg.walk():
            filename, fallback_ext = _image_part_info(part)
            if not filename:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            digest = hashlib.sha256(payload).hexdigest()
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
            if not Path(safe_name).suffix:
                safe_name += fallback_ext
            path = PHOTO_DIR / f"{digest[:16]}_{safe_name}"
            if not path.exists():
                path.write_bytes(payload)
            images.append((path, safe_name, digest))

        if not images:
            skipped += 1
            continue

        inserted = 0
        with connect() as con:
            for i, (path, name, digest) in enumerate(images):
                msg_key = message_id if len(images) == 1 else f"{message_id}#{i+1}"
                try:
                    con.execute("""
                        INSERT INTO photos(
                            message_id, sender_email, sender_name, email_subject, email_body,
                            received_at, image_path, image_name, image_hash, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
                    """, (msg_key, sender_email, sender_name, subject, body, received_iso,
                          str(path), name, digest))
                    inserted += 1
                    added += 1
                except Exception:
                    pass

        if inserted > 0:
            client.store(seq, "+FLAGS", "\\Deleted")
            deleted += 1

    if deleted:
        client.expunge()
    client.logout()

    return {
        "ok": True,
        "message": f"Sincronizzazione completata: {added} foto nuove, {deleted} email eliminate, {skipped} senza foto",
        "added": added,
        "deleted": deleted,
        "skipped": skipped,
    }
