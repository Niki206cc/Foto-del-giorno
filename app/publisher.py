import html
import smtplib
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime
from .db import connect, get_settings


def _paragraphs(text):
    chunks = [x.strip() for x in (text or "").split("\n\n") if x.strip()]
    return "\n".join(f"<p>{html.escape(x).replace(chr(10), '<br>')}</p>" for x in chunks)


def _footer_html(text, public_email, site_home_url):
    safe = html.escape(text or "").replace(chr(10), "<br>")

    if public_email:
        escaped_email = html.escape(public_email)
        mailto = f'<a href="mailto:{html.escape(public_email, quote=True)}">{escaped_email}</a>'
        safe = safe.replace(escaped_email, mailto)

    if site_home_url:
        brand = "Montagne &amp; Paesi"
        brand_link = f'<a href="{html.escape(site_home_url, quote=True)}">{brand}</a>'
        safe = safe.replace(brand, brand_link)

    chunks = [x.strip() for x in safe.split("<br><br>") if x.strip()]
    return "\n".join(f"<p>{x}</p>" for x in chunks)


def _author_html(author):
    author = (author or "").strip()
    if not author:
        return ""
    return f"<p><strong>Foto di:</strong> {html.escape(author)}</p>"


def _pcustom_block(name, value):
    """Genera uno shortcode Postie Shortcodes AddOn per salvare un custom field.

    Il blocco viene inserito dentro un contenitore nascosto: se l'add-on non fosse
    attivo, gli shortcode non compariranno comunque visivamente nell'articolo HTML.
    """
    value = (value or "").strip()
    if not value:
        return ""
    return f'[pcustom name="{name}"]{html.escape(value)}[/pcustom]'


def _photo_custom_fields_html(row):
    fields = [
        _pcustom_block("foto_autore", row["author"]),
        _pcustom_block("foto_luogo", row["location"]),
        _pcustom_block("foto_provincia", row["province"]),
        _pcustom_block("foto_data", row["shot_date"]),
    ]
    fields = [x for x in fields if x]
    if not fields:
        return ""
    return "<div style='display:none'>" + "\n".join(fields) + "</div>"


def build_postie_message(row):
    s = get_settings()
    category = (s.get("postie_category") or "").strip()
    category_id = (s.get("postie_category_id") or "").strip()

    # Postie supporta categoria o ID categoria nel subject tra parentesi quadre.
    # Se è configurato l'ID numerico, viene preferito perché evita ambiguità tra nomi simili.
    category_token = category_id if category_id.isdigit() else category
    subject = f"[{category_token}] {row['title']}" if category_token else row["title"]

    public_email = (s.get("photo_public_email") or "").strip()
    site_home_url = (s.get("site_home_url") or "https://www.montagneepaesi.com/").strip()
    footer = (s.get("footer_text") or "").replace("{email_foto}", public_email)
    tags = (s.get("postie_tags") or "").strip()

    # I custom fields vengono passati a WordPress tramite lo shortcode [pcustom]
    # del Postie Shortcodes AddOn. Elementor potrà poi leggerli come campi dinamici.
    body_parts = [
        "<p><strong>Foto del giorno</strong></p>",
        _paragraphs(row["article_text"]),
        _author_html(row["author"]),
        _photo_custom_fields_html(row),
    ]

    if tags:
        # Manteniamo i tag in fondo per non sporcare l'anteprima social.
        body_parts.append(f"<p style='display:none'>tags: {html.escape(tags)}</p>")

    body_parts.extend([
        "<hr>",
        _footer_html(footer, public_email, site_home_url),
    ])
    body_html = "\n".join(x for x in body_parts if x)

    # La parte plain resta pulita: niente shortcode tecnici visibili.
    plain_parts = ["Foto del giorno", row["article_text"] or ""]
    if (row["author"] or "").strip():
        plain_parts.append(f"Foto di: {row['author'].strip()}")
    plain_parts.append(footer)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = s["smtp_from"] or s["smtp_user"]
    msg["To"] = s["postie_to"]
    msg.set_content("\n\n".join(x for x in plain_parts if x))
    msg.add_alternative(body_html, subtype="html")

    image_path = Path(row["image_path"])
    if image_path.exists():
        ext = image_path.suffix.lower()
        subtype = "jpeg" if ext in (".jpg", ".jpeg") else ext.lstrip(".") or "jpeg"
        msg.add_attachment(image_path.read_bytes(), maintype="image", subtype=subtype, filename=row["image_name"] or image_path.name)
    return msg


def send_to_postie(photo_id):
    s = get_settings()
    needed = ["smtp_host", "smtp_user", "smtp_password", "postie_to"]
    missing = [k for k in needed if not s.get(k)]
    if missing:
        raise RuntimeError("Configurazione SMTP/Postie incompleta: " + ", ".join(missing))

    with connect() as con:
        row = con.execute("SELECT * FROM photos WHERE id=?", (photo_id,)).fetchone()
    if not row:
        raise RuntimeError("Foto non trovata")

    msg = build_postie_message(row)
    port = int(s.get("smtp_port") or 587)
    smtp = smtplib.SMTP(s["smtp_host"], port, timeout=30)
    try:
        smtp.ehlo()
        if s.get("smtp_tls") == "1":
            smtp.starttls()
            smtp.ehlo()
        smtp.login(s["smtp_user"], s["smtp_password"])
        smtp.send_message(msg)
    finally:
        smtp.quit()

    now = datetime.now().astimezone().isoformat()
    with connect() as con:
        con.execute("""
            UPDATE photos
            SET status='sent', sent_at=?, published_at=?, last_error=NULL, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (now, now, photo_id))
