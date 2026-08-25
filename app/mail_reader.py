import email
import hashlib
import imaplib
import re
from email.header import decode_header, make_header
from pathlib import Path
from datetime import datetime
from .db import connect, get_settings

PHOTO_DIR = Path("/app/data/photos")
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

def decode(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value

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

def sync_mail():
    s = get_settings()
    if not s["imap_host"] or not s["imap_user"] or not s["imap_password"]:
        return {"ok": False, "message": "IMAP non configurato", "added": 0}

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    port = int(s.get("imap_port") or 993)
    client = imaplib.IMAP4_SSL(s["imap_host"], port) if s.get("imap_ssl") == "1" else imaplib.IMAP4(s["imap_host"], port)
    client.login(s["imap_user"], s["imap_password"])
    client.select(s.get("imap_folder") or "INBOX")

    typ, data = client.search(None, "UNSEEN")
    if typ != "OK":
        client.logout()
        return {"ok": False, "message": "Errore ricerca IMAP", "added": 0}

    added = 0
    for uid in data[0].split():
        typ, raw = client.fetch(uid, "(RFC822)")
        if typ != "OK":
            continue
        msg = email.message_from_bytes(raw[0][1])
        message_id = msg.get("Message-ID") or f"imap-{uid.decode()}"
        subject = decode(msg.get("Subject"))
        sender_raw = decode(msg.get("From"))
        sender_name, sender_email = email.utils.parseaddr(sender_raw)
        body = extract_text(msg)
        received = msg.get("Date", "")
        try:
            received_dt = email.utils.parsedate_to_datetime(received)
            received_iso = received_dt.isoformat()
        except Exception:
            received_iso = datetime.now().astimezone().isoformat()

        images = []
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype not in ALLOWED_TYPES:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            filename = decode(part.get_filename()) or f"foto{ALLOWED_TYPES[ctype]}"
            digest = hashlib.sha256(payload).hexdigest()
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
            path = PHOTO_DIR / f"{digest[:16]}_{safe_name}"
            if not path.exists():
                path.write_bytes(payload)
            images.append((path, safe_name, digest))

        if not images:
            continue

        # MVP: una riga per ogni immagine allegata
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
                    added += 1
                except Exception:
                    pass
        client.store(uid, "+FLAGS", "\\Seen")

    client.logout()
    return {"ok": True, "message": f"Sincronizzazione completata: {added} foto nuove", "added": added}
