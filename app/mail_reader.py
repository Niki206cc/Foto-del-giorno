import email
import hashlib
import html
import imaplib
import re
import smtplib
from email.header import decode_header, make_header
from email.message import EmailMessage
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


def extract_instagram_username(text):
    text = text or ""
    patterns = [
        r"(?:instagram|nome\s*utente\s*instagram|username\s*instagram)\s*[:\-]\s*(?:https?://(?:www\.)?instagram\.com/)?@?([A-Za-z0-9._]{1,30})",
        r"(?:instagram|nome\s*utente\s*instagram|username\s*instagram)\s+@?([A-Za-z0-9._]{1,30})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return match.group(1).strip().lstrip("@").rstrip("/")
    return ""


def extract_form_email(text):
    text = text or ""
    patterns = [
        r"(?im)^\s*(?:email|e-mail|indirizzo\s+email)\s*:\s*([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})\s*$",
        r"(?i)\b([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I | re.M)
        if match:
            return match.group(1).strip()
    return ""


def extract_form_name(text):
    """Legge il nome inserito nel modulo Elementor, evitando il nome mittente tecnico."""
    text = text or ""
    patterns = [
        r"(?im)^\s*(?:nome\s+e\s+cognome|nome\s+completo|nome)\s*:\s*([^\r\n]+?)\s*$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = html.unescape(match.group(1)).strip()
            value = re.sub(r"\s+", " ", value)
            if value and "@" not in value and len(value) <= 100:
                return value
    return ""


def _social_link(icon, label, url):
    url = (url or "").strip()
    if not url:
        return ""
    return (
        f'<li style="margin:7px 0;">'
        f'<span style="display:inline-block;width:24px;">{html.escape(icon)}</span>'
        f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
        f'{html.escape(label)}</a></li>'
    )


def send_thank_you_email(recipient, name=""):
    s = get_settings()
    if s.get("thank_you_enabled") != "1" or not recipient:
        return False
    needed = ["smtp_host", "smtp_user", "smtp_password"]
    if any(not s.get(k) for k in needed):
        return False

    clean_name = html.unescape((name or "").strip())
    greeting = f"Ciao {html.escape(clean_name)}," if clean_name else "Ciao,"
    social_links = "".join(filter(None, [
        _social_link("🌐", "Sito Montagne & Paesi", s.get("site_home_url")),
        _social_link("📷", "Instagram", s.get("social_instagram_url")),
        _social_link("🔵", "Facebook", s.get("social_facebook_url")),
        _social_link("✈️", "Telegram", s.get("social_telegram_url")),
        _social_link("💬", "WhatsApp", s.get("social_whatsapp_url")),
    ]))

    body_html = f"""
    <p>{greeting}</p>
    <p>grazie per aver inviato la tua foto a <strong>Montagne &amp; Paesi</strong>.</p>
    <p>La redazione la valuterà per la pubblicazione nella rubrica <strong>La foto del giorno</strong>.</p>
    <p>Nel frattempo puoi seguirci qui:</p>
    <ul style="list-style:none;padding-left:0;margin-left:0;">{social_links}</ul>
    <p>Grazie per contribuire a raccontare il nostro territorio!</p>
    <p><strong>Montagne &amp; Paesi</strong></p>
    """.strip()

    plain_links = []
    for icon, label, key in [
        ("🌐", "Sito", "site_home_url"),
        ("📷", "Instagram", "social_instagram_url"),
        ("🔵", "Facebook", "social_facebook_url"),
        ("✈️", "Telegram", "social_telegram_url"),
        ("💬", "WhatsApp", "social_whatsapp_url"),
    ]:
        url = (s.get(key) or "").strip()
        if url:
            plain_links.append(f"{icon} {label}: {url}")
    greeting_plain = f"Ciao {clean_name}," if clean_name else "Ciao,"
    body_plain = "\n\n".join([
        greeting_plain,
        "Grazie per aver inviato la tua foto a Montagne & Paesi.",
        "La redazione la valuterà per la pubblicazione nella rubrica La foto del giorno.",
        "Nel frattempo puoi seguirci qui:\n" + "\n".join(plain_links),
        "Grazie per contribuire a raccontare il nostro territorio!\n\nMontagne & Paesi",
    ])

    msg = EmailMessage()
    msg["Subject"] = (s.get("thank_you_subject") or "Grazie per averci inviato la tua foto!").strip()
    msg["From"] = s.get("smtp_from") or s.get("smtp_user")
    msg["To"] = recipient
    msg.set_content(body_plain)
    msg.add_alternative(body_html, subtype="html")

    smtp = smtplib.SMTP(s["smtp_host"], int(s.get("smtp_port") or 587), timeout=30)
    try:
        smtp.ehlo()
        if s.get("smtp_tls") == "1":
            smtp.starttls()
            smtp.ehlo()
        smtp.login(s["smtp_user"], s["smtp_password"])
        smtp.send_message(msg)
    finally:
        smtp.quit()
    return True


def _already_imported(message_id):
    with connect() as con:
        row = con.execute(
            "SELECT 1 FROM photos WHERE message_id=? OR message_id LIKE ? LIMIT 1",
            (message_id, message_id + "#%"),
        ).fetchone()
    return row is not None


def _image_part_info(part):
    ctype = (part.get_content_type() or "").lower()
    filename = decode(part.get_filename()).strip()
    ext = Path(filename).suffix.lower() if filename else ""

    if ctype in ALLOWED_TYPES:
        fallback_ext = ALLOWED_TYPES[ctype]
        return filename or f"foto{fallback_ext}", fallback_ext

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
    thanked = 0

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
        instagram_username = extract_instagram_username(body)
        form_email = extract_form_email(body)
        form_name = extract_form_name(body)
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
                            received_at, image_path, image_name, image_hash, instagram_username, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
                    """, (msg_key, form_email or sender_email, form_name or sender_name, subject, body, received_iso,
                          str(path), name, digest, instagram_username))
                    inserted += 1
                    added += 1
                except Exception:
                    pass

        if inserted > 0:
            recipient = form_email or sender_email
            thank_name = form_name or ""
            try:
                if recipient and send_thank_you_email(recipient, thank_name):
                    thanked += 1
            except Exception:
                pass
            client.store(seq, "+FLAGS", "\\Deleted")
            deleted += 1

    if deleted:
        client.expunge()
    client.logout()

    return {
        "ok": True,
        "message": f"Sincronizzazione completata: {added} foto nuove, {deleted} email eliminate, {skipped} senza foto, {thanked} ringraziamenti inviati",
        "added": added,
        "deleted": deleted,
        "skipped": skipped,
        "thanked": thanked,
    }
