"""A bit of fun between sets and at the finish: G-rated GIFs from GIPHY, plus encouragement lines.

How it follows GIPHY's API terms (developers.giphy.com):
* One free key for the whole app (the owner's, kept on the server in .env or Streamlit secrets). A free key allows
  100 searches an hour, so each search's results are cached for 6 hours and reused by everyone.
* rating=g only, from a short list of friendly searches. GIFs are shown from GIPHY's own URLs (never downloaded or
  re-hosted), with the "Powered by GIPHY" mark next to them.
* Without a key, or if GIPHY can't be reached, nothing breaks: the encouragement line still shows.
People can turn GIFs off in You > Fun GIFs.
"""
import random

import requests
import streamlit as st

import config

SEARCH_URL = "https://api.giphy.com/v1/gifs/search"
MOMENTS = {  # moment: (searches, encouragement lines)
    "rest": (["you got this", "keep going", "lets go"],
             ["You've got this.", "Breathe. Next set is yours.", "Strong work so far.", "One set at a time.",
              "Shake it out. You're doing great."]),
    "done": (["nailed it", "high five", "you did it", "great job"],
             ["Workout done. That counts.", "You showed up. That's the hard part.", "Nice work today."]),
    "pr": (["new record", "champion", "celebration dance"],
           ["New record!", "Look at you go.", "That's a new best."]),
}


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _search(query):
    """URLs of G-rated GIFs for one search, cached for 6 hours (one call serves every visitor)."""
    try:
        r = requests.get(SEARCH_URL, params={"api_key": config.GIPHY_API_KEY, "q": query, "limit": 25,
                                             "rating": "g", "lang": "en"}, timeout=6)
        r.raise_for_status()
        out = []
        for g in r.json().get("data", []):
            img = (g.get("images") or {}).get("fixed_height") or {}
            url = img.get("webp") or img.get("url")
            if url and g.get("rating") == "g":
                out.append(url)
        return out
    except (requests.RequestException, ValueError):
        return []


def enabled(username):
    import session_data

    return bool(config.GIPHY_API_KEY) and session_data.settings(username).get("gifs", True)


def line(moment):
    """An encouragement line for the moment, the same one for the rest of this screen."""
    key = f"_fun_line_{moment}"
    if key not in st.session_state:
        st.session_state[key] = random.choice(MOMENTS[moment][1])
    return st.session_state[key]


def new_round(moment):
    """Pick a fresh GIF and line next time (call when a new rest starts or a workout finishes)."""
    st.session_state.pop(f"_fun_line_{moment}", None)
    st.session_state.pop(f"_fun_gif_{moment}", None)


def show(username, moment, height=150):
    """The line, and a GIF under it when GIFs are on. Returns True if a GIF was shown."""
    st.markdown(f"<p style='text-align:center;font-weight:650;margin:.4rem 0'>{line(moment)}</p>",
                unsafe_allow_html=True)
    if not enabled(username):
        return False
    key = f"_fun_gif_{moment}"
    if key not in st.session_state:
        urls = _search(random.choice(MOMENTS[moment][0]))
        st.session_state[key] = random.choice(urls) if urls else None
    url = st.session_state[key]
    if not url:
        return False
    st.html(f'<div style="text-align:center"><img src="{url}" alt="" style="height:{height}px;max-width:100%;'
            'border-radius:14px"><div style="font-size:.7rem;opacity:.6;margin-top:2px">Powered by GIPHY</div></div>')
    return True
