"""Small shared UI helpers so every page behaves the same way."""
import html
import re
from datetime import date

import streamlit as st

import ai

CSS = """
<style>
/* One quiet design language: Inter type, 8px rhythm, soft borders, one accent colour. */
.block-container { padding-top: 2.5rem; padding-bottom: 4rem; max-width: 880px; }
/* Buttons never span a wide screen edge to edge (it reads as a banner, not a button). Phones keep full-width
   actions at the bottom, where a thumb reaches them; from 640px up a button is at most 400px wide. */
@media (min-width: 640px) {
  [data-testid="stMain"] .stButton { max-width: 400px; }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] .stButton { max-width: none; }
  .st-key-bs-donebar .stButton { margin-inline: auto; }
}
/* type scale: page title 2.1 / section 1.25 / item 1.05 / body 1 / caption .85 (same on every page) */
h1 { font-size: 2.1rem !important; font-weight: 700 !important; letter-spacing: -.025em; padding-bottom: .25rem; }
h2 { font-size: 1.5rem !important; }
h3 { font-size: 1.25rem !important; }
h4, h5 { font-size: 1.05rem !important; }
h2, h3, h4, h5 { font-weight: 650 !important; letter-spacing: -.015em; }
[data-testid="stCaptionContainer"], .stCaption { opacity: .72; line-height: 1.5; }
[data-testid="stMetricValue"] { font-weight: 650; letter-spacing: -.02em; }
[data-testid="stMetricLabel"] { opacity: .7; }

/* cards: hairline border that warms up on hover */
/* no boxes: sections breathe and are separated by a single hairline, not a frame */
div[data-testid="stVerticalBlockBorderWrapper"] { border: none !important; border-top: 1px solid rgba(139,92,246,.22) !important;
  border-radius: 0 !important; background: transparent !important; box-shadow: none !important; padding: 1.1rem 0 .4rem !important; }

/* buttons: content-width on desktop (full-width bars look heavy), a little lift and press response */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button, .stLinkButton > a {
  border-radius: 12px; font-weight: 550; transition: transform .08s ease, border-color .18s ease, background-color .18s ease; }
.stButton > button:hover, .stFormSubmitButton > button:hover { transform: translateY(-1px); }
.stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(0) scale(.985); }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondaryFormSubmit"] { padding-inline: 1.4rem; }

/* sidebar: our own navigation, calm section labels */
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarUserContent"] { padding-top: 1rem; }
.bs-nav-h { font-size: .7rem; letter-spacing: .09em; text-transform: uppercase; opacity: .5; margin: 1.1rem 0 .25rem .5rem; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] { border-radius: 10px; padding-block: .35rem; }

/* logo = a real, clickable vector that takes you Home */
.st-key-logo_home button { background: url("/app/static/logo.svg") left center / contain no-repeat !important;
  border: none !important; box-shadow: none !important; height: 46px; min-height: 46px; width: 178px; padding: 0;
  margin: .25rem 0 .5rem; opacity: .95; transition: opacity .15s ease, transform .15s ease; }
.st-key-logo_home button:hover { opacity: 1; transform: scale(1.03); background-color: transparent !important; }
.st-key-logo_home button p, .st-key-logo_home button span { display: none; }

/* week flames: seven across on every screen size (st.columns would stack on a phone) */
.bs-flames { display: flex; justify-content: space-between; gap: .25rem; }
.bs-day { display: flex; flex-direction: column; align-items: center; flex: 1; gap: .1rem; font-size: .72rem; }
.bs-flame { font-family: 'Material Symbols Rounded'; font-size: 36px; line-height: 1; font-weight: normal;
  font-variation-settings: 'FILL' 0, 'wght' 300; user-select: none; }
.bs-day.next .bs-flame { color: rgba(139,92,246,.45); }
.bs-day.past .bs-flame { color: currentColor; opacity: .28; }
.bs-day.today:not(.on) .bs-flame { color: var(--bs-accent-ink, #7C3AED); font-variation-settings: 'FILL' 0, 'wght' 500;
  filter: drop-shadow(0 0 6px rgba(168,85,247,.55)); }
.bs-day.today .bs-lab { opacity: 1; font-weight: 700; }
.bs-day.on .bs-flame { font-variation-settings: 'FILL' 1; color: transparent;
  background: linear-gradient(180deg, #ffd1ef 0%, #ec4899 40%, #8b5cf6 100%); -webkit-background-clip: text; background-clip: text;
  filter: drop-shadow(0 0 8px rgba(236,72,153,.55)); }
.bs-day.today.on .bs-flame { animation: bs-flicker 2.6s ease-in-out infinite; }
.bs-lab { opacity: .6; }
.bs-week { margin: .5rem 0 1.4rem; font-size: 1rem; }
.bs-week b { font-weight: 650; }
.bs-back { margin: -.4rem 0 1.4rem; padding: .9rem 1rem; border-radius: 14px; background: rgba(139,92,246,.10); line-height: 1.5; font-size: .95rem; }
.bs-flame { color: color-mix(in srgb, currentColor 45%, transparent); }
.bs-day.today .bs-lab { opacity: 1; font-weight: 700; }
.bs-day.today:not(.on) .bs-flame { color: color-mix(in srgb, currentColor 75%, transparent); }
@keyframes bs-flicker { 0%,100% { transform: scale(1) rotate(-1.5deg); } 50% { transform: scale(1.09) rotate(1.5deg); } }

/* "keep-" rows: picture + text + action stay side by side on a phone (Streamlit would stack them) */
[class*="st-key-keep-"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; align-items: center; gap: .75rem; }
[class*="st-key-keep-"] [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; }
.st-key-keep-pb-top [data-testid="stColumn"]:last-child .stButton { margin-left: auto; width: fit-content; }
/* Numbers save as you change them, so Streamlit's "Press Enter to apply" hint only confuses. */
[data-testid="InputInstructions"] { display: none !important; }
/* two equal buttons or boxes side by side (beats the picture-row rule above) */
div.st-key-keep-tpl-actions div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div.st-key-keep-pb-top div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div.st-key-keep-pl-actions div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[class*="st-key-keep-phase-"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[class*="st-key-keep-skmove-"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[class*="st-key-keep-tpl-ed-"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[class*="st-key-keep-pb-nav"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[class*="-fdone"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div.st-key-keep-pause-more div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[class*="st-key-keep-fb-day-"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div.st-key-keep-nu-meal div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[class*="st-key-keep-plan-amt-"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[class*="st-key-keep-skpair-"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]
{ flex: 1 1 0 !important; width: auto !important; }
[class*="st-key-keep-"] [data-testid="stColumn"]:first-child { flex: 0 0 auto !important; }
[class*="st-key-keep-"] [data-testid="stColumn"]:not(:first-child):not(:last-child) { flex: 1 1 0 !important; }
[class*="st-key-keep-"] [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; }
[class*="st-key-keep-"] [data-testid="stImage"] img { border-radius: 12px; aspect-ratio: 1 / 1; object-fit: cover; }
/* a card that uses its whole width: header line, equal photo tiles, details under each */
.bs-ch { display: flex; flex-wrap: wrap; align-items: baseline; gap: .35rem .75rem; margin-bottom: .75rem; }
.bs-ct { font-size: 1.5rem; font-weight: 700; letter-spacing: -.02em; }
.bs-chip2 { font-size: .8rem; padding: .15rem .65rem; border-radius: 999px; background: rgba(139,92,246,.18); }
.bs-meta { margin-left: auto; font-size: .85rem; opacity: .65; }
.bs-tiles { display: grid; grid-template-columns: repeat(var(--cols, 2), 1fr); gap: .85rem; margin-bottom: .25rem; }
@media (max-width: 640px) { .bs-tiles { grid-template-columns: repeat(2, 1fr); } }
.bs-tile img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 12px; background: rgba(139,92,246,.12); display: block; }
.bs-tile-t { font-weight: 600; margin-top: .55rem; line-height: 1.25; }
.bs-tile-c { opacity: .65; font-size: .85rem; }
/* set rows: fixed label and tick columns so every row lines up, number boxes share the rest */
[class*="st-key-keep-set"] [data-testid="stColumn"]:first-child { flex: 0 0 5.5rem !important; }
[class*="st-key-keep-set"] [data-testid="stColumn"]:last-child { flex: 0 0 4.5rem !important; }
[class*="st-key-keep-set"] { gap: 0; }
.bs-strip { display: flex; gap: .5rem; overflow: hidden; }
.bs-strip img { width: 25%; max-width: 110px; aspect-ratio: 1; object-fit: cover; border-radius: 12px; background: rgba(139,92,246,.12); }

/* palette: purple (main) with pink and blue accents; soft glows behind everything, light or dark */
:root { --bs-grad: linear-gradient(135deg, #7c3aed 0%, #c026d3 55%, #ec4899 100%); }
[data-testid="stApp"] {
  background-image:
    radial-gradient(900px 520px at 88% -8%, rgba(139,92,246,.20), transparent 60%),
    radial-gradient(760px 520px at -8% 28%, rgba(59,130,246,.13), transparent 60%),
    radial-gradient(640px 420px at 62% 112%, rgba(236,72,153,.11), transparent 60%);
  background-attachment: fixed; }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--bs-grad) !important; border: none !important; color: #fff !important;
  box-shadow: 0 6px 18px rgba(168,85,247,.32); }
[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.08); box-shadow: 0 8px 24px rgba(236,72,153,.35); }
/* visible choices (pills) in the same gradient when selected */
[data-testid="stBaseButton-pillsActive"], [data-testid="stBaseButton-segmented_controlActive"], [data-testid="stButtonGroup"] button[data-selected="true"] {
  background: var(--bs-grad) !important; color: #fff !important; border-color: transparent !important; }
[data-testid="stBaseButton-pills"], [data-testid="stBaseButton-segmented_control"] { border-radius: 999px; }
.bs-thumb { width: 72px; height: 72px; border-radius: 14px; object-fit: cover; display: block; background: rgba(139,92,246,.12); }
.bs-thumb.sm { width: 56px; height: 56px; border-radius: 12px; }

/* hero band: a full-width photo that fades into the page, with the headline on top */
.bs-hero { --img: linear-gradient(135deg, #6d28d9, #db2777); position: relative; overflow: hidden; min-height: 250px; display: flex; flex-direction: column; justify-content: flex-end;
  padding: 1.6rem 1.75rem; border-radius: 28px; color: #fff;
  background: linear-gradient(90deg, rgba(10,8,30,.92) 0%, rgba(10,8,30,.62) 42%, rgba(10,8,30,.05) 100%), var(--img) center 30% / cover no-repeat; }
.bs-kicker { font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; opacity: .8; font-weight: 600; }
.bs-hero-title { font-size: 2.6rem; font-weight: 750; letter-spacing: -.03em; line-height: 1.05; margin: .25rem 0 .35rem; }
.bs-hero-meta { opacity: .8; font-size: .95rem; }
/* track list: numbered rows with a small moving picture, like a playlist */
.bs-track { display: flex; align-items: center; gap: 1rem; padding: .7rem 0; border-top: 1px solid rgba(139,92,246,.18); }
.bs-track:first-child { border-top: none; }
.bs-track .n { width: 1.6rem; opacity: .45; font-weight: 600; font-variant-numeric: tabular-nums; }
.bs-track img { width: 64px; min-width: 64px; height: 64px; border-radius: 14px; object-fit: cover; flex: none; background: rgba(139,92,246,.12); }
.bs-track .t { font-weight: 600; line-height: 1.25; }
.bs-track .ph { width: 64px; min-width: 64px; height: 64px; border-radius: 14px; flex: none; display: grid; place-items: center;
  background: rgba(139,92,246,.12); color: var(--bs-accent-ink); font-family: 'Material Symbols Rounded'; font-size: 28px; }
.bs-track .d { opacity: .62; font-size: .85rem; }
.bs-track .w { font-size: .85rem; line-height: 1.35; margin-top: .15rem; opacity: .85; }
.bs-track .w b { color: var(--bs-accent-ink); font-weight: 600; }
/* stepped line: where you are on a skill ladder */
.bs-steps { display: flex; align-items: center; margin: .5rem 0 .25rem; }
.bs-dot { width: 26px; height: 26px; border-radius: 50%; flex: none; display: grid; place-items: center; font-size: .72rem; font-weight: 700;
  border: 2px solid rgba(139,92,246,.4); opacity: .8; }
.bs-dot.done { background: rgba(139,92,246,.45); border-color: transparent; opacity: 1; }
.bs-dot.now { background: var(--bs-grad); border-color: transparent; color: #fff; opacity: 1; box-shadow: 0 0 0 5px rgba(168,85,247,.22); }
.bs-line { height: 2px; flex: 1; background: rgba(139,92,246,.3); min-width: 6px; }
.bs-line.done { background: linear-gradient(90deg, rgba(139,92,246,.7), rgba(236,72,153,.7)); }
/* icon tile where there is no photo */
.bs-thumb.ic { display: grid; place-items: center; background: var(--bs-grad); color: #fff; font-family: 'Material Symbols Rounded'; font-size: 34px; }

/* touch: 44px targets and full-width primary actions on phones, where a thumb needs them */
@media (max-width: 640px), (pointer: coarse) {
  .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button, .stLinkButton > a { min-height: 44px; }
  [data-baseweb="input"] input, [data-baseweb="select"] > div, textarea { min-height: 44px; }
  [data-testid="stBaseButton-primary"] { width: 100%; }
  .block-container { padding-top: 1.5rem; padding-left: 1rem; padding-right: 1rem; }
  h1 { font-size: 1.75rem !important; }
  [data-testid="stImage"] img { max-height: 240px; object-fit: contain; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)
    dark = is_dark()  # accent for icons on soft circles: readable on both backgrounds
    st.html("<style>:root { --bs-page-bg: %s; --bs-accent-ink: %s; --bs-accent-soft: %s; }</style>" % (
        ("#0A0A14", "#D6BCFF", "rgba(168,85,247,.28)") if dark else ("#F6F3FF", "#7C3AED", "rgba(124,58,237,.12)")))


def demo(path_or_url, max_h="46vh"):
    """A moving exercise demo. Use this, not st.image: st.image re-encodes animated WebP and keeps one frame."""
    if not path_or_url:
        return
    url = str(path_or_url)
    if not url.startswith(("/app/", "http", "data:")):  # a file under ./static: serve it as-is
        from exercise_data import static_url
        url = static_url(url)
    st.html(f'<img src="{html.escape(url)}" alt="" style="width:100%;max-height:{max_h};object-fit:contain;'
            'border-radius:16px;display:block">')


def thumb(url, size="md"):
    """A crisp square thumbnail (served at 4x the displayed size, so it stays sharp on phones)."""
    if url:
        st.html(f'<img class="bs-thumb{" sm" if size == "sm" else ""}" src="{html.escape(url)}" alt="" loading="lazy">')


def icon_thumb(name):
    st.html(f'<div class="bs-thumb ic">{html.escape(name)}</div>')


def hero(kicker, title, meta, image_url):
    """A full-width photo band with the headline over it (not a card)."""
    style = f"--img:url('{html.escape(image_url)}')" if image_url else ""
    st.html(f'<div class="bs-hero" style="{style}"><div class="bs-kicker">{html.escape(kicker)}</div>'
            f'<div class="bs-hero-title">{html.escape(title)}</div><div class="bs-hero-meta">{html.escape(meta)}</div></div>')


def _works_html(text):
    """'Works: deep core. Keeps...' with the area in bold accent, so the eye finds what a move is for."""
    head, _, rest = text.partition(". ")
    return f'<div class="w"><b>{html.escape(head)}.</b> {html.escape(rest)}</div>' if text else ""


def tracklist(rows, numbered=True):
    """Rows with a small picture, numbered when order matters (a plan): rows = [(image_url, title, detail)], or
    (image_url, title, detail, works) to add what the move works and why (targets.works)."""
    out = "".join(
        '<div class="bs-track">' + (f'<span class="n">{i:02d}</span>' if numbered else "")
        + (f'<img src="{html.escape(r[0])}" alt="" loading="lazy">' if r[0]
           else '<span class="ph">fitness_center</span>')  # no picture (your own exercise without photos)
        + f'<div><div class="t">{html.escape(r[1])}</div><div class="d">{html.escape(r[2])}</div>'
        + (_works_html(r[3]) if len(r) > 3 else "") + '</div></div>'
        for i, r in enumerate(rows, 1)
    )
    st.html(f'<div>{out}</div>')


CHIME_JS = """<script>
(() => {  /* a soft two-note chime made in the browser (no sound file), plus a short buzz on phones that support it */
  try {
    const A = window.AudioContext || window.webkitAudioContext; const c = new A();
    [[784, 0], [1047, .16]].forEach(([f, t]) => {
      const o = c.createOscillator(), g = c.createGain(); o.type = "sine"; o.frequency.value = f;
      g.gain.setValueAtTime(0.0001, c.currentTime + t); g.gain.exponentialRampToValueAtTime(0.18, c.currentTime + t + .02);
      g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + t + .6); o.connect(g).connect(c.destination);
      o.start(c.currentTime + t); o.stop(c.currentTime + t + .65); });
  } catch (e) {}
  try { navigator.vibrate && navigator.vibrate([120, 80, 120]); } catch (e) {}
})();
</script>"""


def ping():
    """Ask for a chime on the next full run (rest over, a hold finished). Played by play_pending()."""
    st.session_state["_chime"] = True


TOP_JS = """<script>
for (const sel of ['[data-testid="stMain"]', '[data-testid="stAppViewContainer"]', '.main']) {
  const el = document.querySelector(sel); if (el) el.scrollTo({top: 0});
}
window.scrollTo({top: 0});
</script>"""


def to_top():
    """Ask for the page to start at the top on the next run (a new step of a flow, not a refresh of the same one).
    Streamlit keeps the scroll position between reruns, so without this a new step can open mid-way down."""
    st.session_state["_top"] = True


def play_pending(enabled=True):
    """Runs once per page run (homepage.py): one-off browser actions asked for during the run before."""
    if st.session_state.pop("_chime", False) and enabled:
        st.html(CHIME_JS, unsafe_allow_javascript=True, width=1)
    if st.session_state.pop("_top", False):
        st.html(TOP_JS, unsafe_allow_javascript=True, width=1)


SAVED_CSS = """<style>
.bs-saved { display: flex; align-items: center; gap: .9rem; padding: .85rem 1rem; border-radius: 16px; background: rgba(34,197,94,.10); margin: .4rem 0; }
.bs-saved .pics { display: flex; flex: none; }
.bs-saved .pics img { width: 38px; height: 38px; border-radius: 10px; object-fit: cover; border: 2px solid var(--bs-page-bg, #fff);
  margin-left: -12px; opacity: 0; animation: bs-pop .32s ease-out forwards; }
.bs-saved .pics img:first-child { margin-left: 0; }
.bs-saved .ok { width: 30px; height: 30px; flex: none; border-radius: 50%; background: #16A34A; display: grid; place-items: center;
  margin-left: -8px; opacity: 0; animation: bs-pop .3s ease-out forwards; }
.bs-saved .ok::after { content: ""; width: 7px; height: 13px; border: solid #fff; border-width: 0 3px 3px 0; border-radius: 1px;
  transform: translateY(-1px) rotate(45deg) scale(0); animation: bs-tick .25s ease-out forwards; animation-delay: inherit; }
.bs-saved .t { font-weight: 650; line-height: 1.3; }
.bs-saved .d { font-size: .88rem; opacity: .75; line-height: 1.35; }
@keyframes bs-pop { from { opacity: 0; transform: scale(.6); } to { opacity: 1; transform: none; } }
@keyframes bs-tick { to { transform: translateY(-1px) rotate(45deg) scale(1); } }
@media (prefers-reduced-motion: reduce) { .bs-saved .pics img, .bs-saved .ok, .bs-saved .ok::after { animation: none; opacity: 1; } .bs-saved .ok::after { transform: translateY(-1px) rotate(45deg); } }
</style>"""


def saved(title, detail, images=()):
    """Says an action is done, where people are looking (not a corner toast): the items' pictures, then a tick.
    Saving is instant, so there is no fake wait; the short pop-in (under a second) only marks the moment."""
    pics = list(dict.fromkeys(u for u in images if u))[:4]  # each picture once
    imgs = "".join(f'<img src="{html.escape(u)}" alt="" style="animation-delay:{i * 90}ms">' for i, u in enumerate(pics))
    tick = f'<span class="ok" style="animation-delay:{len(pics) * 90}ms"></span>'
    st.html(SAVED_CSS + f'<div class="bs-saved" role="status"><div class="pics">{imgs}{tick}</div>'
            f'<div><div class="t">{html.escape(title)}</div><div class="d">{html.escape(detail)}</div></div></div>')


CREATED_CSS = """<style>
.bs-made { display:flex; align-items:center; gap:14px; padding:14px 16px; border-radius:18px; margin:6px 0 12px;
  background: var(--bs-accent-soft); }
.bs-made .stack { display:flex; align-items:center; flex:0 0 auto; }
.bs-made .stack img { width:46px; height:46px; border-radius:12px; object-fit:cover; margin-left:-16px;
  border:2px solid var(--bs-accent-soft); box-shadow:0 2px 8px rgba(0,0,0,.18); opacity:0;
  animation: bsSlide .42s cubic-bezier(.2,.8,.2,1) forwards; }
.bs-made .stack img:first-child { margin-left:0; }
.bs-made .ok { width:30px; height:30px; border-radius:50%; margin-left:-10px; background:#16a34a; position:relative;
  transform:scale(0); animation: bsPop .32s ease-out forwards; flex:0 0 auto; z-index:2; }
.bs-made .ok::after { content:""; position:absolute; left:10px; top:6px; width:7px; height:13px;
  border:solid #fff; border-width:0 3px 3px 0; transform:rotate(45deg); }
.bs-made .txt { opacity:0; animation: bsFade .35s ease-out forwards; }
.bs-made .k { font-size:.72rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--bs-accent-ink); }
.bs-made .t { font-weight:700; font-size:1.05rem; line-height:1.2; }
.bs-made.big { flex-direction: column; text-align: center; background: transparent; padding: .4rem 0 .8rem; gap: 16px; }
.bs-made.big .stack img { width: 76px; height: 76px; border-radius: 18px; margin-left: -26px; }
.bs-made.big .stack img:first-child { margin-left: 0; }
.bs-made.big .ok { width: 44px; height: 44px; margin-left: -16px; }
.bs-made.big .ok::after { left: 15px; top: 8px; width: 10px; height: 20px; border-width: 0 4px 4px 0; }
.bs-made.big .t { font-size: 1.45rem; font-weight: 800; letter-spacing: -.02em; }
.bs-made.big .k { font-size: .8rem; }
@keyframes bsSlide { from { opacity:0; transform:translateX(-36px); } to { opacity:1; transform:none; } }
@keyframes bsPop { 0% { transform:scale(0); } 70% { transform:scale(1.15); } 100% { transform:scale(1); } }
@keyframes bsFade { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:none; } }
@media (prefers-reduced-motion: reduce) { .bs-made * { animation-duration:1ms !important; animation-delay:0ms !important; } }
</style>"""


def created(kicker, title, images=(), big=True):
    """Something new was made: its pictures slide in from the left and stack, then a tick, then its name.
    big=True is the pop-up version: centred, larger pictures, the name underneath."""
    pics = list(dict.fromkeys(u for u in images if u))[:5]
    imgs = "".join(f'<img src="{html.escape(u)}" alt="" style="animation-delay:{i * 120}ms">' for i, u in enumerate(pics))
    t = len(pics) * 120
    st.html(CREATED_CSS + f'<div class="bs-made{" big" if big else ""}" role="status"><div class="stack">{imgs}'
            f'<span class="ok" style="animation-delay:{t}ms"></span></div>'
            f'<div class="txt" style="animation-delay:{t + 150}ms"><div class="k">{html.escape(kicker)}</div>'
            f'<div class="t">{html.escape(title)}</div></div></div>')


def stepper(total, current, done=False):
    """Dots on a line: finished steps filled, the current step glowing, the rest outlined."""
    parts = []
    for i in range(total):
        state = "done" if (i < current or done) else "now" if i == current else ""
        parts.append(f'<div class="bs-dot {state}">{"✓" if state == "done" else i + 1}</div>')
        if i < total - 1:
            parts.append(f'<div class="bs-line {"done" if (i < current or done) else ""}"></div>')
    st.html(f'<div class="bs-steps" role="img" aria-label="Step {min(current + 1, total)} of {total}">{"".join(parts)}</div>')


def keep(*keys):
    """Restore widget values saved by remember(): call at the top of a page, before its widgets.
    Streamlit forgets a page's inputs when you leave it; this keeps what you typed."""
    for k in keys:
        backup = st.session_state.get("_bk_" + k)
        if k not in st.session_state and backup is not None:
            st.session_state[k] = backup


def remember(*keys):
    """Save widget values so keep() can restore them after you come back: call at the end of a page."""
    for k in keys:
        if k in st.session_state:
            st.session_state["_bk_" + k] = st.session_state[k]


def forget(*prefixes):
    """Drop remembered values (after a successful save the form should start fresh)."""
    for k in list(st.session_state):
        if any(k.startswith(p) or k.startswith("_bk_" + p) for p in prefixes):
            st.session_state.pop(k, None)


def card_header(title, chip=None, meta=None):
    """Title, a small chip and a right-aligned note on one line (wraps on a phone)."""
    chip_html = f'<span class="bs-chip2">{html.escape(chip)}</span>' if chip else ""
    meta_html = f'<span class="bs-meta">{html.escape(meta)}</span>' if meta else ""
    st.html(f'<div class="bs-ch"><span class="bs-ct">{html.escape(title)}</span>{chip_html}{meta_html}</div>')


def tiles(items):
    """Equal photo tiles that fill the card: items = [(image_url, title, caption)]."""
    cells = "".join(
        f'<div class="bs-tile">' + (f'<img src="{html.escape(url)}" alt="" loading="lazy">' if url else "")
        + f'<div class="bs-tile-t">{html.escape(title)}</div><div class="bs-tile-c">{html.escape(caption)}</div></div>'
        for url, title, caption in items
    )
    cols = max(2, min(len(items), 4))  # one tile takes half the row, 2-4 share it
    st.html(f'<div class="bs-tiles" style="--cols:{cols}">{cells}</div>')


def photo_strip(urls):
    """A row of equal square photos that stays one row on any screen."""
    imgs = "".join(f'<img src="{u}" alt="" loading="lazy">' for u in urls if u)
    if imgs:
        st.html(f'<div class="bs-strip">{imgs}</div>')


def logo_button(home_page):
    """The logo, as a crisp vector button. Clicking it goes Home without logging you out."""
    if st.button("BodySync home", key="logo_home", help="Go to Home"):
        st.switch_page(home_page)


def nav_heading(text):
    st.markdown(f"<div class='bs-nav-h'>{text}</div>", unsafe_allow_html=True)


def flames(dots, today=None):
    """Seven flames for the week (Mon..Sun): filled purple when trained, a glowing outline for today, soft purple
    for days still to come, and a faint outline for days that passed (quiet on purpose).
    Plain HTML so it stays seven-across on a phone. No streak counter, nothing to 'lose'."""
    today = date.today().weekday() if today is None else today
    names = "MTWTFSS"
    def state(i, hit):  # done / today / coming up / missed (missed is quiet, never red: no guilt)
        return "on" if hit else "today" if i == today else "next" if i > today else "past"
    cells = "".join(
        f'<div class="bs-day {state(i, hit)}{" today" if i == today and hit else ""}">'
        f'<span class="bs-flame">local_fire_department</span><span class="bs-lab">{names[i]}</span></div>'
        for i, hit in enumerate(dots)
    )
    label = ", ".join(n for n, hit in zip(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], dots) if hit) or "none yet"
    st.html(f'<div class="bs-flames" role="img" aria-label="Days trained this week: {label}">{cells}</div>')


def empty_state(title, hint, icon="eco"):
    """A calm 'nothing here yet' message. Distinct from errors and loading."""
    with st.container(border=True):
        st.markdown(f"#### :material/{icon}: {title}")
        st.caption(hint)


def _use_key():
    key = st.session_state.get("ai_key_input", "").strip()
    if key:
        st.session_state["user_gemini_key"] = key
        st.session_state["ai_key_input"] = ""
        st.toast("Key added. AI features are on for this session.", icon=":material/check_circle:")


def _forget_key():
    st.session_state.pop("user_gemini_key", None)
    st.toast("Key removed.", icon=":material/delete:")


def ai_key_notice(username=None):
    """How AI works on this copy, up front. With the owner's key (server-side) there's nothing to set up: just a
    daily allowance. Pasting your own free key is optional; it lives only in this browser session."""
    if st.session_state.get("user_gemini_key"):
        c1, c2 = st.columns([4, 1], vertical_alignment="center")
        c1.caption(":material/key: Using your own Gemini key (kept only in this session, never saved)")
        c2.button("Remove", on_click=_forget_key, key="ai_forget_key", width="stretch")
        return
    if ai.is_configured():  # the app owner's key: no setup for anyone
        left = ai.uses_left(username) if username else None
        if left is not None:
            st.caption(f":material/auto_awesome: {left} of {ai.DAILY_LIMIT} AI requests left today. "
                       "AI answers can be wrong; check anything important.")
        if left == 0 or st.session_state.get("ai_show_own"):
            _own_key_box()
        elif left is not None and st.button("Use my own key instead", key="ai_own_btn", type="tertiary"):
            st.session_state["ai_show_own"] = True
            st.rerun()
        return
    with st.container(border=True):
        st.markdown("**:material/key: AI isn't set up on this copy yet**")
        st.caption("The person running this app can add one free Gemini key for everyone (see DEPLOY.md). "
                   "Or paste your own free key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey); "
                   "it stays in this browser session only and is never saved.")
        _own_key_box(border=False)


def _own_key_box(border=True):
    with st.container(border=border):
        st.caption("Only paste a free-tier key you can delete later (no billing on its project). Not sure about "
                   "pasting a key here? Leave it: everything else in BodySync works without AI.")
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        c1.text_input("Gemini API key", type="password", key="ai_key_input", label_visibility="collapsed",
                      placeholder="Paste your Gemini API key", on_change=_use_key)
        c2.button("Use key", on_click=_use_key, type="primary", width="stretch", key="ai_use_key")


def badges(*items):
    """Render small colored labels, skipping empty values."""
    colors = ["violet", "blue", "green", "orange", "gray"]
    text = " ".join(f":{colors[i % len(colors)]}-badge[{x.title()}]" for i, x in enumerate(items) if x)
    if text:
        st.markdown(text)


def no_media(text):
    """AI text, shown safely: no Markdown images (they would load a picture from any web address the AI wrote) and
    no hidden links (a link shows its words only). Everything else (bold, lists, tables) still formats."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", str(text or ""))
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)


def stream_into_chat(generator, placeholder_text="Thinking..."):
    """Stream an AI answer inside an assistant bubble. Shows a status line until
    the first words arrive so a click always gets an immediate response.
    Returns the full text."""
    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        waiting = st.empty()
        waiting.caption(placeholder_text)

        def wrapped():
            first = True
            for piece in generator:
                if first:
                    waiting.empty()
                    first = False
                yield piece.replace("![", "[")  # no Markdown images from AI text (see no_media)

        try:
            return st.write_stream(wrapped())
        except Exception as e:  # show the problem inside the bubble, not above an empty one
            waiting.empty()
            st.error(ai.friendly_error(e))
            return None
        finally:
            waiting.empty()


ART = "/app/static/illustrations/"
ART_CREDIT = ("Illustrations by [pikisuperstar](https://www.magnific.com/author/pikisuperstar), "
              "[redgreystock](https://www.magnific.com/author/redgreystock) and "
              "[macrovector](https://www.magnific.com/author/macrovector) on Magnific")
ART_CREDIT_HTML = ('Illustrations by <a href="https://www.magnific.com/author/pikisuperstar" target="_blank">pikisuperstar</a>, '
                   '<a href="https://www.magnific.com/author/redgreystock" target="_blank">redgreystock</a> and '
                   '<a href="https://www.magnific.com/author/macrovector" target="_blank">macrovector</a> on Magnific')


def is_dark():
    """True when the app is showing its dark theme (follows the device, or the user's choice in the menu)."""
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


def split_vars():
    """Colours for the split pages (sign-in and onboarding), as CSS variables, for the current theme.
    The pictures are drawn on white: in light mode they blend into the page (multiply), in dark mode they sit as a
    rounded picture with no frame, border or shadow."""
    if is_dark():
        v = {"page": "#0A0A14", "ink": "#EDEBFF", "soft": "#B8B3DD", "faint": "#8C87B5",
             "line": "rgba(237,235,255,.16)", "hover": "rgba(237,235,255,.06)",
             "panel": "linear-gradient(165deg, #1B1640 0%, #1A1233 55%, #26112E 100%)",
             "blend": "normal",
             "pick": "#C4A1FF", "pickbg": "rgba(168,85,247,.18)",
             "gbg": "#131314", "gline": "#8E918F", "gink": "#E3E3E3"}
    else:
        v = {"page": "#FFFFFF", "ink": "#1B1740", "soft": "#57527A", "faint": "#7A759C",
             "line": "rgba(27,23,64,.14)", "hover": "rgba(27,23,64,.04)",
             "panel": "linear-gradient(165deg, #F1ECFF 0%, #F6EEFD 55%, #FDEEF6 100%)",
             "blend": "multiply",
             "pick": "#7C3AED", "pickbg": "rgba(124,58,237,.09)",
             "gbg": "#FFFFFF", "gline": "#747775", "gink": "#1F1F1F"}
    return ":root { " + " ".join(f"--sp-{k}: {val};" for k, val in v.items()) + " }"


TAB_CSS = """
<style>
/* Phone and tablet (under 1024px): a bottom tab bar, always visible (visible navigation is found more often than a
   hidden menu: NN/g), and no collapsed sidebar behind a ">>" button. Laptop: the sidebar does this job. Pages in focus mode (onboarding, a live workout) skip it. */
.st-key-bs-tabbar { display: none !important; }
@media (min-width: 1024px) { .st-key-bs-more { display: none !important; } }
.st-key-bs-more [data-testid="stPageLink"] a { padding: .7rem .2rem; border-bottom: 1px solid rgba(139,92,246,.14); border-radius: 0; }
@media (max-width: 1023px) {
  header[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none !important; }
  .block-container { padding-bottom: 6.5rem !important; padding-top: 1.25rem !important; }
  .st-key-bs-tabbar { display: grid !important; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0 !important; position: fixed; left: 0; right: 0; bottom: 0;
    z-index: 999; padding: 6px 6px calc(6px + env(safe-area-inset-bottom)); box-sizing: border-box; width: 100% !important;
    background: color-mix(in srgb, var(--bs-tab-bg) 86%, transparent); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    border-top: 1px solid var(--bs-tab-line); }
  .st-key-bs-tabbar > div { width: auto !important; min-width: 0; }
  [data-testid="stLayoutWrapper"]:has(> .st-key-bs-donebar) { bottom: calc(66px + env(safe-area-inset-bottom)) !important; }
  .st-key-bs-tabbar [data-testid="stPageLink"] a { flex-direction: column; gap: 2px; padding: 6px 2px; min-height: 52px; justify-content: center; border-radius: 12px; background: transparent !important; }
  .st-key-bs-tabbar [data-testid="stPageLink"] a span[data-testid="stIconMaterial"] { font-size: 24px; color: var(--bs-tab-off) !important; }
  .st-key-bs-tabbar [data-testid="stPageLink"] a p { font-size: .68rem !important; font-weight: 600; color: var(--bs-tab-off) !important; white-space: nowrap; margin: 0; }
}
</style>
"""


BAR_CSS = """<style>
/* Continue bar: a workout or skill practice in progress follows you to every tab (like a music app's mini player). */
[data-testid="stLayoutWrapper"]:has(> .st-key-bs-cbar) { position: fixed; z-index: 998; left: 50%; transform: translateX(-50%);
  bottom: 16px; width: min(560px, calc(100% - 24px)) !important; }
.st-key-bs-cbar { background: var(--bs-tab-bg); border: 1px solid var(--bs-tab-line); border-radius: 18px;
  box-shadow: 0 8px 24px rgba(40,20,90,.10); padding: 8px 10px 8px 8px; }
.st-key-bs-cbar [data-testid="stHorizontalBlock"] { align-items: center; flex-wrap: nowrap !important; gap: .6rem; }
.st-key-bs-cbar [data-testid="stColumn"] { min-width: 0 !important; }
.st-key-bs-cbar [data-testid="stColumn"]:last-child { flex: 0 0 52px !important; width: 52px !important; }
.st-key-bs-cbar button { width: 46px !important; height: 46px; min-height: 46px; border-radius: 50% !important; padding: 0 !important;
  background: var(--bs-accent-soft) !important; border: none !important; box-shadow: none !important; }
.st-key-bs-cbar button span[data-testid="stIconMaterial"] { color: var(--bs-accent-ink) !important; font-size: 26px; margin: 0 !important; }
.st-key-bs-cbar button:hover { filter: brightness(1.1); }
.bs-cbar { display: flex; align-items: center; gap: .65rem; min-width: 0; }
.bs-cbar img, .bs-cbar .ic { width: 46px; height: 46px; border-radius: 12px; object-fit: cover; flex: none; }
.bs-cbar .ic { display: grid; place-items: center; background: var(--bs-grad); color: #fff; font-family: 'Material Symbols Rounded'; font-size: 26px; }
.bs-cbar .k { font-size: .72rem; opacity: .6; font-weight: 500; }
.bs-cbar .t { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bs-cbar .d { font-size: .82rem; opacity: .7; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.block-container { padding-bottom: 9rem !important; }
@media (max-width: 1023px) {
  [data-testid="stLayoutWrapper"]:has(> .st-key-bs-cbar) { bottom: calc(72px + env(safe-area-inset-bottom)); }
  .block-container { padding-bottom: 12rem !important; }
}
</style>"""


def continue_bar(pages, here):
    """Shown on other tabs while a workout or skill practice is unfinished: what you're on, and one tap back."""
    if here == "home":  # Home shows a big Continue card
        return
    sess, skp = st.session_state.get("sess"), st.session_state.get("skp")
    if sess:
        import today
        from exercise_data import find_exercise, mini_url

        cur = today._current(sess)
        total = sum(len(i["rows"]) for i in sess["items"])
        done = sum(1 for i in sess["items"] for r in i["rows"] if r["d"])
        ex = find_exercise(today._media_name(cur)) if cur else None
        pic = mini_url(ex) if ex else None
        kicker, title = "Continue workout", (cur["exercise"] if cur else "All sets done")
        detail = f"{sess.get('source') or 'Workout'} · {done} of {total} sets"
        target, label = "workout", "Continue"
    elif skp:
        import skills_logic as sk_

        lad = sk_.all_ladders(__import__("session_data").custom_skills(st.session_state.get("username"))).get(skp["lid"])
        if not lad:
            return
        pic, kicker, title, detail = None, "Continue practice", lad["title"], "Pick up where you left off"
        target, label = "skills", "Continue"
    else:
        return
    st.html(BAR_CSS + "<style>.stApp:has(.st-key-bs-donebar) .st-key-bs-cbar,"
            ".stApp:has(.st-key-bs-donebar) [data-testid='stLayoutWrapper']:has(> .st-key-bs-cbar)"
            "{display:none !important}</style>")  # a screen's own pinned button wins over the Continue bar
    with st.container(key="bs-cbar"):
        a, b = st.columns([6, 1], vertical_alignment="center")
        img = f'<img src="{html.escape(pic)}" alt="">' if pic else '<span class="ic">play_arrow</span>'
        a.html(f'<div class="bs-cbar">{img}<div style="min-width:0"><div class="k">{html.escape(kicker)}</div>'
               f'<div class="t">{html.escape(title)}</div><div class="d">{html.escape(detail)}</div></div></div>')
        if b.button("", icon=":material/play_arrow:", key="bs_cbar_go", help=label):
            if target == "workout":
                st.session_state["t_phase"] = "session"
                to_workout(pages)
            st.switch_page(pages[target])


TAP_CSS = """<style>
/* Tap rows: picture, title, detail; the whole row opens it. An optional button on the right sits above. */
[class*="st-key-tap-"] { position: relative; border-bottom: 1px solid rgba(139,92,246,.14); padding: .35rem 0; }
[class*="st-key-tap-"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; align-items: center; gap: .8rem; }
[class*="st-key-tap-"] [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; }
[class*="st-key-tap-"] [data-testid="stColumn"]:nth-child(2) { flex: 1 1 auto !important; }
[class*="st-key-tap-"] [data-testid="stColumn"]:not(:nth-child(2)) { flex: 0 0 auto !important; }
[class*="st-key-tap-"] [data-testid="stLayoutWrapper"]:has(> [class*="st-key-open-"]) { position: absolute !important; inset: 0; z-index: 1; margin: 0; width: 100% !important; height: 100% !important; }
[class*="st-key-tap-"] [class*="st-key-open-"], [class*="st-key-tap-"] [class*="st-key-open-"] .stButton,
[class*="st-key-tap-"] [class*="st-key-open-"] [data-testid="stElementContainer"],
[class*="st-key-tap-"] [class*="st-key-open-"] button { position: absolute; inset: 0; width: 100% !important; height: 100% !important; opacity: 0; max-width: none !important; cursor: pointer; }
[class*="st-key-tap-"] [data-testid="stColumn"]:last-child .stButton { position: relative; z-index: 2; }
[class*="st-key-tap-"]:hover { background: rgba(139,92,246,.05); border-radius: 12px; }
.bs-tap .t { font-weight: 600; line-height: 1.25; }
.bs-tap .d { font-size: .85rem; opacity: .7; margin-top: .1rem; }
.bs-tap .k { font-size: .72rem; font-weight: 650; letter-spacing: .05em; text-transform: uppercase; opacity: .6; }
.bs-tap .k.now { color: var(--bs-accent-ink); opacity: 1; }
.bs-tap .k.done { color: #16A34A; opacity: 1; }
.bs-tapimg { width: 56px; height: 56px; border-radius: 14px; object-fit: cover; display: block; background: rgba(139,92,246,.10); }
.bs-tapimg.ic { display: grid; place-items: center; font-family: 'Material Symbols Rounded'; font-size: 28px; color: var(--bs-accent-ink); }
</style>"""


def tap_row(key, img, title, detail, kicker="", kicker_state="", action=None, icon=None, end=None, end_on=False):
    """One row you can tap anywhere to open (returns opened, acted). `img` is a URL or an icon name (icon=True).
    `end` swaps the chevron for another icon (e.g. add_circle / check_circle when picking); end_on colours it."""
    st.html(TAP_CSS)
    opened = acted = False
    with st.container(key=f"tap-{key}"):
        cols = st.columns([1, 5, 2] if action else [1, 6, 1], vertical_alignment="center")
        pic = (f'<div class="bs-tapimg ic">{html.escape(img or "fitness_center")}</div>' if icon or not img
               else f'<img class="bs-tapimg" src="{html.escape(img)}" alt="" loading="lazy">')
        cols[0].html(pic)
        cols[1].html('<div class="bs-tap">' + (f'<div class="k {kicker_state}">{html.escape(kicker)}</div>' if kicker else "")
                     + f'<div class="t">{html.escape(title)}</div>' + (f'<div class="d">{html.escape(detail)}</div>' if detail else "")
                     + "</div>")
        if action:
            acted = cols[2].button(action, key=f"tapact-{key}", width="stretch")
        else:
            style = ("color:var(--bs-accent-ink);font-variation-settings:'FILL' 1;opacity:1" if end_on else "opacity:.45")
            cols[2].html(f'<div style="text-align:right;{style};font-family:\'Material Symbols Rounded\';font-size:26px">'
                         f'{html.escape(end or "chevron_right")}</div>')
        with st.container(key=f"open-{key}"):
            opened = st.button(f"Open {title}", key=f"tapopen-{key}")
    return opened, acted


def back_to_you(pages):
    """Pages opened from the You tab (Progress, Exercise library, Nutrition, FitBuddy) get a clear way back."""
    if st.button("You", icon=":material/arrow_back:", key="back_to_you"):
        st.switch_page(pages["profile"])


def go(page_key):
    """Change page in a way that also works from inside a pop-up (st.dialog), where st.switch_page doesn't take
    effect: remember where to go, rerun the whole app, and homepage.py switches page before drawing anything."""
    st.session_state["_goto"] = page_key
    st.rerun()


def to_workout(pages):
    """Open the Workouts tab on purpose (a preview, a live workout, the planner). The tab bar itself always lands
    on Workouts' explore page; only these deliberate jumps go further in."""
    st.session_state["t_go"] = True
    go("workout")


def tab_bar(pages, current=None, keys=("home", "workout", "lifts", "skills", "profile"), labels=None):
    """The phone tab bar: five places, icon over a short label, the current one coloured.
    Streamlit marks the current page link only with a generated class, so we colour it by position."""
    labels = labels or {"home": "Home", "workout": "Workouts", "lifts": "Library", "skills": "Skills", "profile": "You"}
    dark = is_dark()
    st.html("<style>:root { --bs-tab-bg: %s; --bs-tab-line: %s; --bs-tab-off: %s; --bs-tab-on: %s; }</style>" % (
        ("#0A0A14", "rgba(237,235,255,.12)", "#8C87B5", "#C4A1FF") if dark else ("#FFFFFF", "rgba(27,23,64,.10)", "#7A759C", "#7C3AED")))
    st.markdown(TAB_CSS, unsafe_allow_html=True)
    if current in keys:
        n = keys.index(current) + 1
        sel = f".st-key-bs-tabbar > div:nth-child({n}) a"
        st.html(f"<style>{sel} span[data-testid=stIconMaterial], {sel} p {{ color: var(--bs-tab-on) !important; }}"
                f"{sel} span[data-testid=stIconMaterial] {{ font-variation-settings: 'FILL' 1; }}</style>")
    with st.container(key="bs-tabbar"):
        for k in keys:
            st.page_link(pages[k], label=labels[k])
