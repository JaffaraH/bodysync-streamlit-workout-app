"""The Gemini API, the way apps that offer free AI usually do it: the app owner's key stays on the server and
each person gets a daily allowance, so nobody has to find or paste an API key.

* Owner's key: GEMINI_API_KEY in .env or Streamlit secrets. It's used on the server only; browsers never see it.
* Daily allowance: AI_DAILY_LIMIT requests per person per day (default 20), counted in that person's settings.
  Free-tier Gemini has its own limits per key, so the allowance keeps one busy person from using them all.
* Your own key (optional): someone can paste their own free key; it lives only in their browser session, is never
  saved, and isn't counted against the allowance.
* Models: GEMINI_MODEL first, then a newer stable model if that one is ever retired (a 404 from the API).
* Privacy: on Gemini's free tier, Google may use prompts to improve its products. The app says so where AI is used.
"""
import json
from datetime import date

import config


class AINotConfigured(Exception):
    pass


class DailyLimitReached(Exception):
    pass


MISSING_KEY_HINT = (
    "AI isn't set up on this copy of BodySync yet. The app owner can add a free Gemini key "
    "(aistudio.google.com/apikey), or you can paste your own below."
)
DAILY_LIMIT = int(config._env("AI_DAILY_LIMIT", default="20") or 20)
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash-lite"]  # stable Flash-Lite models (ai.google.dev)


def _session():
    try:
        import streamlit as st

        return st.session_state
    except Exception:
        return {}


def own_key():
    return _session().get("user_gemini_key")


def get_key() -> str:
    """Your own pasted key if there is one, otherwise the app owner's server-side key."""
    return own_key() or config.GEMINI_API_KEY


def is_configured() -> bool:
    return bool(get_key())


def uses_left(username):
    """How many AI requests this person has left today on the owner's key (None = unlimited, their own key)."""
    if own_key():
        return None
    import session_data

    s = session_data.settings(username)
    used = s.get("ai_used", 0) if s.get("ai_day") == date.today().isoformat() else 0
    return max(0, DAILY_LIMIT - used)


def _count(username):
    if own_key() or not username:
        return
    import session_data

    s = session_data.settings(username)
    today = date.today().isoformat()
    used = s.get("ai_used", 0) if s.get("ai_day") == today else 0
    session_data.save_settings(username, ai_day=today, ai_used=used + 1)


def _check(username):
    if not is_configured():
        raise AINotConfigured(MISSING_KEY_HINT)
    left = uses_left(username) if username else None
    if left is not None and left <= 0:
        raise DailyLimitReached(f"You've used today's {DAILY_LIMIT} AI requests. They reset tomorrow, or paste your "
                                "own free key to keep going.")


def friendly_error(e: Exception) -> str:
    if isinstance(e, (AINotConfigured, DailyLimitReached)):
        return str(e)
    text = str(e).lower()
    if "api key" in text or "api_key" in text or "permission" in text or "401" in text or "403" in text:
        return "Gemini rejected the API key. Check that it was copied in full, or paste a new one."
    if "429" in text or "quota" in text or "rate" in text or "resource_exhausted" in text:
        return "Gemini is busy right now (free usage limit). Wait a minute and try again."
    if "timeout" in text or "connect" in text or "network" in text or "dns" in text:
        return "Couldn't reach Gemini. Check your internet connection and try again."
    return f"Gemini couldn't answer this time ({type(e).__name__}). Try again."


def shrink(image, max_side=1024):
    """Downscale a PIL image before upload: faster, cheaper, less memory."""
    image = image.convert("RGB")
    image.thumbnail((max_side, max_side))
    return image


def _models():
    return list(dict.fromkeys([config.GEMINI_MODEL] + FALLBACK_MODELS))


def _retired(e):
    text = str(e).lower()
    return "404" in text or "not_found" in text or "not found" in text


def stream(prompt: str, image=None, username=None):
    """Yield text chunks from Gemini as they arrive. Counts one request against the daily allowance."""
    _check(username)
    from google import genai

    client = genai.Client(api_key=get_key())
    contents = [prompt, shrink(image)] if image is not None else prompt
    models = _models()
    for i, model in enumerate(models):
        try:
            got = False
            for chunk in client.models.generate_content_stream(model=model, contents=contents):
                if chunk.text:
                    if not got:
                        _count(username)
                        got = True
                    yield chunk.text
            return
        except Exception as e:  # a retired model: try the next one; anything else goes to friendly_error
            if not _retired(e) or i == len(models) - 1:
                raise


def ask_json(prompt: str, image=None, username=None):
    """Ask for a JSON answer (Gemini's JSON mode) and return it parsed. Counts one request."""
    _check(username)
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=get_key())
    contents = [prompt, shrink(image)] if image is not None else prompt
    models = _models()
    for i, model in enumerate(models):
        try:
            r = client.models.generate_content(
                model=model, contents=contents,
                config=types.GenerateContentConfig(response_mime_type="application/json"))
            _count(username)
            return json.loads(r.text)
        except Exception as e:
            if not _retired(e) or i == len(models) - 1:
                raise
