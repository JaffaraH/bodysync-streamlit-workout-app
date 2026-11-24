"""Who is using the app. Two modes, chosen by configuration (nothing to manage either way):

* local  (default): no sign-in. One person, data kept in a local file on this computer.
* google (when an [auth] section exists in Streamlit secrets): Streamlit's built-in
  "Sign in with Google"; workouts are saved in the person's own Google Drive.
"""
import os
import sqlite3

import streamlit as st

import config
import ui

GOOGLE_G = "data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 48 48%22><path fill=%22%23EA4335%22 d=%22M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z%22/><path fill=%22%234285F4%22 d=%22M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z%22/><path fill=%22%23FBBC05%22 d=%22M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z%22/><path fill=%22%2334A853%22 d=%22M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z%22/></svg>"


def mode():
    return "google" if config.AUTH_CONFIGURED else "local"




def on_private_network():
    """True when the app is opened on this computer or a home network (localhost, 192.168.x, 10.x, *.local).

    Local mode has no sign-in: everyone who opens it is the same person. That's fine on your own computer, but a
    public copy (a fork deployed without Google sign-in) would let every visitor see the same data. So local mode
    only runs on a private address. BODYSYNC_ALLOW_SHARED=1 turns this off on purpose (a private server you trust).
    """
    if os.environ.get("BODYSYNC_ALLOW_SHARED", "") == "1":
        return True
    try:
        host = (st.context.headers.get("Host") or "").split(":")[0].strip("[]").lower()
    except Exception:  # no request context (tests, scripts)
        return True
    return (host in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or host.endswith(".local")
            or host.startswith(("192.168.", "10.")) or any(host.startswith(f"172.{n}.") for n in range(16, 32)))


def setup_needed():
    """Shown instead of the app when a public copy has no sign-in set up (see on_private_network)."""
    st.title("This copy of BodySync needs sign-in set up")
    st.write("It's running on a public address without Google sign-in, so everyone who opened it would share one "
             "account and see each other's workouts. To keep people's data private, it won't open like this.")
    st.markdown("**If you run this copy:** add the `[auth]` section to your Streamlit secrets "
                "(see `.streamlit/secrets.toml.example` and DEPLOY.md). Each person then signs in with Google and "
                "their data is saved in their own Google Drive.")
    st.caption("Running it only for yourself on a private server? Set BODYSYNC_ALLOW_SHARED=1.")


def profiles_enabled():
    """Local test accounts: set BODYSYNC_PROFILES=1 to get a 'Who's training?' picker (no Google needed)."""
    return mode() == "local" and os.environ.get("BODYSYNC_PROFILES", "") == "1"


def identity():
    """(username, display name). Local mode is one person on their own machine, or named test profiles."""
    if mode() == "google":
        user = st.user
        email = user.get("email") or "google-user"
        name = user.get("given_name") or user.get("name") or email.split("@")[0]
        return email, name
    if profiles_enabled():
        who = st.session_state.get("local_user", "me")
        return who, who
    return "me", ""


def signed_in():
    if profiles_enabled():
        return bool(st.session_state.get("local_user"))
    return mode() == "local" or bool(st.user.is_logged_in)


def _known_users():
    names = set()
    try:
        conn = sqlite3.connect(config.DB_PATH)
        for table in ("lifts", "workout_sets", "user_prefs", "profiles"):
            try:
                names |= {r[0] for r in conn.execute(f"SELECT DISTINCT username FROM {table}") if r[0]}
            except sqlite3.Error:
                pass
        conn.close()
    except sqlite3.Error:
        pass
    return sorted(names)


def _pick(name):
    st.session_state["local_user"] = name.strip()


def picker():
    """Test accounts on this computer: pick a person or add a new one. Each has separate saved data."""
    _shell_css()
    with st.container(key="sp-shell"):
        with st.container(key="sp-main"):
            st.html(LOGO_HTML)
            st.html('<h1 class="sp-h">Who\'s training?</h1>'
                    '<p class="sp-p">Test accounts on this computer. Each person has their own lifts, skills and progress.</p>')
            st.html(PHONE_PIC)
            with st.container(key="sp-people"):
                for name in _known_users():
                    st.button(f"Continue as {name}", key=f"pick_{name}", on_click=_pick, args=(name,), width="stretch")
                new = st.text_input("New person", placeholder="Type a name and press Enter", key="pick_new")
            if new.strip():
                _pick(new)
                st.rerun()
            _credit_link()
            st.html('<div class="sp-end"></div>')
        _art()


# Sign-in and the test-account picker share one split layout (docs/DESIGN.md, sign-in):
# laptop: a plain column for the words and the button, beside a rounded tinted panel with the pictures.
# phone and tablet: the panel becomes a band at the top and the words follow, one column, nothing hidden.
# Colours come from ui.split_vars(), so light and dark mode both get their own palette.
LANDING_CSS = """
<style>
[data-testid="stApp"] { background: var(--sp-page) !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"], header { display: none !important; }
.block-container { max-width: none !important; padding: 0 !important; }
.st-key-sp-shell { display: grid !important; grid-template-columns: minmax(0, 1fr) minmax(0, 1.12fr); min-height: 100vh; gap: 0 !important; }
.st-key-sp-shell > [data-testid="stLayoutWrapper"] { width: auto !important; min-width: 0; }
[data-testid="stVerticalBlock"]:has(> [data-testid="stLayoutWrapper"] > .st-key-sp-shell) { gap: 0 !important; }
.st-key-sp-shell, .st-key-sp-shell p, .st-key-sp-shell h1, .st-key-sp-shell h3, .st-key-sp-shell label { color: var(--sp-ink); }

/* words column: logo at the top, the message centred in the remaining height */
.st-key-sp-main { min-height: 100vh; box-sizing: border-box; padding: clamp(28px, 4vh, 48px) clamp(32px, 6vw, 96px); gap: 0 !important; }
.st-key-sp-main > * { max-width: 420px; width: 100% !important; }
.st-key-sp-main > :first-child { margin-bottom: auto; }
.st-key-sp-main > :last-child { margin-top: auto; }
.sp-logo { display: block; height: 40px; width: auto; }
.sp-h { font-size: clamp(2.1rem, 3.2vw, 2.9rem) !important; font-weight: 700 !important; letter-spacing: -.03em; line-height: 1.06; margin: 0 0 .9rem; padding: 0 !important; }
.sp-p { font-size: 1.06rem; line-height: 1.55; color: var(--sp-soft) !important; margin: 0 0 1.8rem; }
.sp-note { font-size: .86rem; line-height: 1.55; color: var(--sp-faint) !important; margin: 1rem 0 0; }
.sp-note a, .sp-credit a { color: var(--sp-pick) !important; text-decoration: underline; text-underline-offset: 2px; }

/* Google button, following Google's branding colours for light and dark themes */
.st-key-signin button { height: 50px; border-radius: 999px !important; padding-left: 2.8rem;
  background: var(--sp-gbg) url("__G__") no-repeat 22px center / 20px !important;
  border: 1px solid var(--sp-gline) !important; box-shadow: none !important; transition: filter .15s ease; }
.st-key-signin button:hover { filter: brightness(.97); border-color: var(--sp-gline) !important; }
.st-key-signin button:focus-visible { outline: 3px solid var(--sp-pick); outline-offset: 2px; }
.st-key-signin button p { color: var(--sp-gink) !important; font-family: Roboto, Inter, sans-serif; font-weight: 500; font-size: 1rem; }

/* test-account rows */
.st-key-sp-people button { justify-content: flex-start; height: 50px; border-radius: 14px !important; background: transparent !important;
  border: 1px solid var(--sp-line) !important; padding: 0 1.1rem; }
.st-key-sp-people button:hover { background: var(--sp-hover) !important; border-color: var(--sp-pick) !important; }
.st-key-sp-people input { color: var(--sp-ink) !important; }

/* art panel: inset, rounded, softly tinted. The pictures sit on a white mat, never cropped. */
.st-key-sp-art { margin: 16px; width: calc(100% - 32px) !important; min-height: calc(100vh - 32px); box-sizing: border-box; border-radius: 28px; background: var(--sp-panel);
  padding: 40px clamp(24px, 4vw, 64px) 22px; align-items: center; gap: 0 !important; }
.st-key-sp-art > * { width: 100% !important; display: flex; justify-content: center; }
.st-key-sp-art > :first-child { margin-top: auto; margin-bottom: auto; }
.bs-slides { margin: 0 auto; width: min(100%, 640px, calc((100vh - 280px) * 1.38)); }
.bs-stage { display: grid; }
.bs-slide { grid-area: 1 / 1; opacity: 0; animation: bs-cycle 18s infinite both; transition: opacity .35s ease; }
.bs-slide:nth-child(2) { animation-delay: 6s; } .bs-slide:nth-child(3) { animation-delay: 12s; }
.bs-slide .pic { aspect-ratio: 1.38; }
.bs-slide .pic img, .sp-pic img { width: 100%; height: 100%; object-fit: contain; display: block; border-radius: 18px; mix-blend-mode: var(--sp-blend); }
.bs-slide h3 { font-size: 1.3rem !important; font-weight: 650 !important; letter-spacing: -.02em; margin: 1.4rem 0 .3rem; padding: 0 !important; }
.bs-slide p { font-size: .98rem; margin: 0; color: var(--sp-soft) !important; line-height: 1.5; }
@keyframes bs-cycle { 0% { opacity: 0; } 4% { opacity: 1; } 32% { opacity: 1; } 36% { opacity: 0; } 100% { opacity: 0; } }
.bs-dots { display: flex; gap: 6px; margin: 1.1rem 0 0; }
.bs-dots label { padding: 8px 2px; cursor: pointer; display: flex; align-items: center; }  /* a bigger tap target */
.bs-dots input { position: absolute; opacity: 0; width: 1px; height: 1px; pointer-events: none; }
.bs-dots i { width: 8px; height: 8px; border-radius: 99px; background: var(--sp-line); animation: bs-dot 18s infinite both;
  transition: width .25s ease, background .25s ease; }
.bs-dots label:nth-child(2) i { animation-delay: 6s; } .bs-dots label:nth-child(3) i { animation-delay: 12s; }
.bs-dots input:focus-visible + i { outline: 2px solid var(--sp-pick); outline-offset: 3px; }
@keyframes bs-dot { 0% { background: var(--sp-line); width: 8px; } 4% { background: var(--sp-pick); width: 24px; } 32% { background: var(--sp-pick); width: 24px; } 36% { background: var(--sp-line); width: 8px; } 100% { background: var(--sp-line); width: 8px; } }
/* a dot was tapped: stop the timer and show that slide */
.bs-slides:has(input:checked) .bs-slide, .bs-slides:has(input:checked) .bs-dots i { animation: none; }
.bs-slides:has(input:checked) .bs-slide { opacity: 0; }
.bs-slides:has(input:checked) .bs-dots i { background: var(--sp-line); width: 8px; }
.bs-slides:has(input[value="1"]:checked) .bs-slide:nth-child(1),
.bs-slides:has(input[value="2"]:checked) .bs-slide:nth-child(2),
.bs-slides:has(input[value="3"]:checked) .bs-slide:nth-child(3) { opacity: 1; }
.bs-slides:has(input:checked) .bs-dots input:checked + i { background: var(--sp-pick); width: 24px; }
.sp-credit { font-size: .74rem; color: var(--sp-faint) !important; margin: 1.6rem 0 0; }
.sp-pic { margin: 0 0 1.6rem; }
.st-key-sp-credit { margin-top: .6rem; }
.st-key-sp-credit button, .st-key-sp-privacy button { min-height: 0; padding: 0; }
.st-key-sp-privacy button p, .st-key-sp-credit button p { font-size: .8rem !important; color: var(--sp-faint) !important; text-decoration: underline; text-underline-offset: 2px; }
.sp-phone-only { display: none !important; }
@media (prefers-reduced-motion: reduce) { .bs-slide, .bs-dots i { animation: none; } .bs-slides:not(:has(input:checked)) .bs-slide:first-child { opacity: 1; } .bs-slides:not(:has(input:checked)) .bs-dots label:first-child i { background: var(--sp-pick); width: 24px; } }

/* phone and tablet: one column, the pictures as a band on top */
@media (max-width: 899px) {
  .st-key-sp-shell { grid-template-columns: minmax(0, 1fr); min-height: 0; }
  /* phone: one column in the usual order (logo, headline, picture, buttons), no separate panel */
  .st-key-sp-shell > [data-testid="stLayoutWrapper"]:has(.st-key-sp-art) { display: none !important; }
  .st-key-sp-main { min-height: 0; padding: 28px 20px 32px; align-items: center; }
  .sp-p { margin-bottom: 1.2rem; }
  .st-key-sp-main > * { max-width: 460px; }
  .st-key-sp-main > :first-child, .st-key-sp-main > :last-child { margin: 0; }
  .sp-desk-only { display: none !important; }
  .sp-phone-only { display: block !important; }
  .sp-h { margin-top: 1.1rem; }
}
@media (max-width: 520px) { .sp-logo { height: 34px; } }
</style>
""".replace("__G__", GOOGLE_G)

LOGO_HTML = '<img class="sp-logo" src="/app/static/logo.svg" alt="BodySync">'

# Three full-size pictures, never cropped. Credited behind a small Credits link (and on the You page, About).
_SLIDE_DATA = [
    ("outdoor.jpg", "Move at your own pace", "Track your progress and build strength without the pressure."),
    ("park.jpg", "Level up one step at a time", "From a first push-up to a first pull-up, each skill is a ladder of small steps."),
    ("home.jpg", "Train anywhere", "At home, at the gym or outside. Your plan comes with you."),
]
# The slides change on their own every 6 seconds; tapping a dot shows that slide and stops the timer. The dots are
# hidden radio buttons inside labels (tap the label, the radio is checked) and CSS :has(:checked) picks the slide,
# so it works with no JavaScript (st.html keeps <label> and <input>).
SLIDES = ('<div class="bs-slides"><div class="bs-stage">' + "".join(
    f'<div class="bs-slide"><div class="pic"><img src="{ui.ART}{img}" alt=""></div><h3>{title}</h3><p>{text}</p></div>'
    for img, title, text in _SLIDE_DATA) + '</div><div class="bs-dots" role="radiogroup" aria-label="Pictures">' + "".join(
    f'<label title="Picture {n}"><input type="radio" name="bs-pick" value="{n}" aria-label="Picture {n}"><i></i></label>'
    for n in range(1, len(_SLIDE_DATA) + 1)) + "</div></div>")

PRIVACY_PATH = config.BASE_DIR / "PRIVACY.md"  # shown inside the app, so every copy shows its own policy


def _shell_css():
    st.html(f"<style>{ui.split_vars()}</style>")
    st.markdown(LANDING_CSS, unsafe_allow_html=True)


def _art():
    with st.container(key="sp-art"):
        st.html(SLIDES)


PHONE_PIC = f'<div class="sp-phone-only sp-pic"><img src="{ui.ART}outdoor.jpg" alt=""></div>'


@st.dialog("How your data is kept", width="large")
def _privacy():
    text = PRIVACY_PATH.read_text() if PRIVACY_PATH.exists() else "No privacy policy in this copy."
    st.markdown(text.split("\n", 1)[1] if text.startswith("#") else text)  # the page already has a title


@st.dialog("Credits")
def _credits():
    st.markdown(ui.ART_CREDIT + ".")
    st.markdown("Exercise photos: the public-domain [Free Exercise DB](https://github.com/yuhonas/free-exercise-db).")
    from exercise_data import credits_text
    if credits_text():
        st.markdown(credits_text())
    st.markdown("Celebration flame: [Noto Emoji](https://github.com/googlefonts/noto-emoji) by Google, "
                "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), recoloured.")


def _credit_link():
    with st.container(key="sp-credit"):
        if st.button("Credits", key="sp_credits", type="tertiary"):
            _credits()


def landing(login):
    """The one screen a signed-out visitor sees: the name, one line about the app and one clear button."""
    _shell_css()
    with st.container(key="sp-shell"):
        with st.container(key="sp-main"):
            st.html(LOGO_HTML)
            st.html('<h1 class="sp-h">Train. Track. Grow.</h1>'
                    '<p class="sp-p">BodySync is a free workout and skills tracker. Log your lifts, learn bodyweight '
                    'skills and watch yourself level up.</p>')
            st.html(PHONE_PIC)
            with st.container(key="signin"):
                st.button("Continue with Google", on_click=login, key="signin_btn", width="stretch")
            st.html('<p class="sp-note">Your workouts are saved to your own Google account. Only you can see them, '
                    "when you're signed in. Not us, and not anyone with a link. You can delete them any time.</p>")
            with st.container(key="sp-privacy"):
                if st.button("How your data is kept", key="sp_privacy", type="tertiary"):
                    _privacy()
            _credit_link()
            st.html('<div class="sp-end"></div>')
        _art()


def reconnect_notice(login):
    """Shown when the Google connection expired. Nothing is lost: unsaved changes stay in the session."""
    with st.container(border=True):
        st.markdown("**Reconnect to Google to keep saving**")
        st.caption("Your Google connection timed out. Anything you did since is still here and will save once you reconnect.")
        st.button("Reconnect Google", type="primary", icon=":material/refresh:", on_click=login, key="reconnect")
