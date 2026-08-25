import base64
import json
import mimetypes
import os
import re
import requests
from .db import get_settings

def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise ValueError("La risposta AI non contiene JSON valido")
        return json.loads(m.group(0))

def analyze_photo(row):
    settings = get_settings()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY non configurata nello Stack/.env")

    path = row["image_path"]
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
    email_context = f"""
MAIL ORIGINALE
Oggetto: {row['email_subject'] or ''}
Mittente: {row['sender_name'] or ''} <{row['sender_email'] or ''}>
Testo:
{row['email_body'] or ''}
"""

    payload = {
        "model": settings["ai_model"],
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": settings["ai_prompt"] + "\n\n" + email_context},
                {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"}
            ]
        }]
    }

    r = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"OpenAI HTTP {r.status_code}: {r.text[:700]}")

    data = r.json()
    # Responses API: cerchiamo i blocchi output_text
    texts = []
    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                texts.append(c.get("text", ""))
    if not texts and data.get("output_text"):
        texts.append(data["output_text"])
    if not texts:
        raise RuntimeError("Nessun testo restituito dall'AI")
    result = _extract_json("\n".join(texts))

    return {
        "title": result.get("title", ""),
        "author": result.get("author", ""),
        "location": result.get("location", ""),
        "province": result.get("province", ""),
        "shot_date": result.get("shot_date", ""),
        "article_text": result.get("article_text", ""),
        "instagram_text": result.get("instagram_text", ""),
        "alt_text": result.get("alt_text", ""),
        "hashtags": result.get("hashtags", ""),
    }
