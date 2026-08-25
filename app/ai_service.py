import base64
import json
import mimetypes
import os
import re
import requests
from .db import get_settings


def _extract_json(text):
    text = (text or "").strip()
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


def _email_context(row):
    return f"""
MAIL ORIGINALE
Oggetto: {row['email_subject'] or ''}
Mittente: {row['sender_name'] or ''} <{row['sender_email'] or ''}>
Testo:
{row['email_body'] or ''}
"""


def _as_text(value, separator=", "):
    """Converte sempre i valori AI in testo compatibile con SQLite/form HTML."""
    if value is None:
        return ""
    if isinstance(value, list):
        return separator.join(_as_text(v, separator) for v in value if v is not None)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _normalize_result(result):
    if not isinstance(result, dict):
        raise ValueError("La risposta AI deve essere un oggetto JSON")
    return {
        "title": _as_text(result.get("title")),
        "author": _as_text(result.get("author")),
        "location": _as_text(result.get("location")),
        "province": _as_text(result.get("province")),
        "shot_date": _as_text(result.get("shot_date")),
        "article_text": _as_text(result.get("article_text"), "\n\n"),
        "instagram_text": _as_text(result.get("instagram_text"), "\n"),
        "alt_text": _as_text(result.get("alt_text"), " "),
        "hashtags": _as_text(result.get("hashtags"), " "),
    }


def _analyze_gemini(row, settings, api_key):
    model = (settings.get("ai_model") or "gemini-2.5-flash").strip()
    path = row["image_path"]
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    image_b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")

    prompt = settings["ai_prompt"] + "\n\n" + _email_context(row)
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": image_b64}}
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.4
        }
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    r = requests.post(
        url,
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:900]}")

    data = r.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "\n".join(p.get("text", "") for p in parts if p.get("text"))
    except Exception:
        raise RuntimeError(f"Risposta Gemini inattesa: {json.dumps(data)[:900]}")
    if not text:
        raise RuntimeError("Gemini non ha restituito testo")
    return _normalize_result(_extract_json(text))


def _analyze_openai(row, settings, api_key):
    model = (settings.get("ai_model") or "gpt-5.6-luna").strip()
    path = row["image_path"]
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")

    payload = {
        "model": model,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": settings["ai_prompt"] + "\n\n" + _email_context(row)},
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
        raise RuntimeError(f"OpenAI HTTP {r.status_code}: {r.text[:900]}")

    data = r.json()
    texts = []
    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                texts.append(c.get("text", ""))
    if not texts and data.get("output_text"):
        texts.append(data["output_text"])
    if not texts:
        raise RuntimeError("OpenAI non ha restituito testo")
    return _normalize_result(_extract_json("\n".join(texts)))


def analyze_photo(row):
    settings = get_settings()
    provider = (settings.get("ai_provider") or "gemini").strip().lower()
    api_key = (settings.get("ai_api_key") or "").strip()

    if not api_key:
        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
        else:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(f"API key {provider} non configurata nelle Impostazioni AI")

    if provider == "gemini":
        return _analyze_gemini(row, settings, api_key)
    if provider == "openai":
        return _analyze_openai(row, settings, api_key)
    raise RuntimeError(f"Provider AI non supportato: {provider}")


def test_ai_connection():
    settings = get_settings()
    provider = (settings.get("ai_provider") or "gemini").strip().lower()
    api_key = (settings.get("ai_api_key") or "").strip()
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("API key non configurata")

    model = (settings.get("ai_model") or "").strip()
    if provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        r = requests.post(
            url,
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": "Rispondi soltanto con OK"}]}]},
            timeout=30,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:700]}")
        return "Connessione Gemini riuscita"

    if provider == "openai":
        r = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "input": "Rispondi soltanto con OK"},
            timeout=30,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"OpenAI HTTP {r.status_code}: {r.text[:700]}")
        return "Connessione OpenAI riuscita"

    raise RuntimeError(f"Provider AI non supportato: {provider}")
