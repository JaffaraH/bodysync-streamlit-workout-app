"""First-run setup for a workout app. Principles (see docs/DESIGN.md, onboarding):
- a short promise first (how many questions, how long), then one question per screen
- progress is always visible (segments + "2 of 5"), Back and Skip are always reachable
- every question says what it changes; every question is skippable
- chips for pick-many, rows with a description for pick-one, big numbers for days
- ends on the first workout, not a settings summary. Not medical advice.
"""
import html
from datetime import date

import streamlit as st

import session_data
import skills_logic as sk
import ui

GOALS = ["Build muscle", "Get stronger", "Lose weight", "Keep my weight", "Stay healthy", "Build stamina",
         "Move better", "Learn a skill"]  # the same goals as Plan my week (plan.GOALS)
GOAL_ICON = {"Build muscle": "fitness_center", "Get stronger": "exercise", "Lose weight": "monitor_weight",
             "Keep my weight": "balance", "Stay healthy": "favorite", "Build stamina": "directions_walk",
             "Move better": "self_improvement", "Learn a skill": "sports_gymnastics"}
FOCUS_OF = {"Build muscle": "strength", "Get stronger": "strength", "Lose weight": "strength", "Keep my weight": "strength",
            "Stay healthy": "explore", "Build stamina": "explore", "Move better": "explore", "Learn a skill": "skills"}
LEVELS = ["Beginner", "Intermediate", "Advanced"]
AREAS = ["Knee", "Shoulder", "Lower back", "Wrist", "Hip", "Ankle", "Neck"]  # matches today.AREA_MUSCLES
CREATE_OWN = "Create my own"
ONBOARD_HIDE = {"pushup-variations"}  # an add-on for after the first push-up; still in Skills > Explore
LEVEL_NOTE = {
    "Beginner": "New to training, or back after months off. We start with easier moves.",
    "Intermediate": "You've trained regularly for 6+ months and know the main lifts.",
    "Advanced": "Years of steady training. Harder moves are included.",
}
SIDE_LABEL = {"goals": "Goals", "skills": "Skills", "days": "Training days", "level": "Fitness level", "area": "Go easy on"}
STEPS = [
    ("goals", "What are you here for?", "Pick any. Home and Plan my week use them, and you can change them any time in You."),
    ("skills", "Which skills do you want to work toward?", "Each starts at a step that suits you, with a clear target. Not listed? Make your own. Skip it if skills aren't for you."),
    ("days", "How many days a week do you want to train?", "Asked once. Home counts your week against it. Missing a week costs you nothing."),
    ("level", "How would you describe your fitness level?", "Decides how hard the suggested exercises are."),
    ("area", "Anything we should go easy on?", "Optional. On exercises that load that area, we'll remind you to keep the range comfortable and skip or swap it if it hurts. This isn't medical advice."),
]

CSS = """
<style>
/* Laptop: a split page. Left, a rounded tinted panel with the five steps (ticked as you go, with your answers)
   and a picture; right, the question at a comfortable reading width. Phone and tablet: one column, progress bar on top.
   Colours come from ui.split_vars() (shared with sign-in), so light and dark mode each get a checked palette. */
[data-testid="stApp"] { background: var(--sp-page) !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; }
header, [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none !important; }
.block-container { max-width: none !important; padding: 0 !important; }
[data-testid="stVerticalBlock"]:has(> [data-testid="stLayoutWrapper"] > .st-key-ob-shell) { gap: 0 !important; }
.st-key-ob-shell { display: grid !important; grid-template-columns: minmax(300px, .82fr) minmax(0, 1.18fr); min-height: 100vh; gap: 0 !important; }
.st-key-ob-shell > [data-testid="stLayoutWrapper"] { width: auto !important; min-width: 0; }
.st-key-ob-shell > [data-testid="stLayoutWrapper"]:has(.st-key-ob-side) { order: -1; }
.st-key-ob-shell p, .st-key-ob-shell label, .st-key-ob-shell b, .bs-ob-h, .bs-ob-intro-h, .ob-steps .t { color: var(--sp-ink); }
.st-key-ob-shell button[kind="primary"] p { color: #fff !important; }

/* side panel */
.st-key-ob-side { margin: 16px; width: calc(100% - 32px) !important; min-height: calc(100vh - 32px); box-sizing: border-box; border-radius: 28px;
  background: var(--sp-panel); padding: 36px clamp(24px, 3vw, 44px) 20px; gap: 0 !important; position: sticky; top: 16px; }
.ob-logo { height: 38px; width: auto; display: block; }
.ob-kick { font-size: .74rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 600; color: var(--sp-faint) !important; margin: 2.6rem 0 1rem; }
.ob-steps { list-style: none; margin: 0; padding: 0; position: relative; }
.ob-steps li { display: grid; grid-template-columns: 30px 1fr; gap: 14px; align-items: start; padding: 0 0 18px; position: relative; }
.ob-steps li:not(:last-child)::after { content: ""; position: absolute; left: 14px; top: 32px; bottom: 4px; width: 2px; background: var(--sp-line); border-radius: 2px; }
.ob-steps li.done:not(:last-child)::after { background: var(--sp-pick); opacity: .45; }
.ob-steps .n { width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; font-size: .82rem; font-weight: 650;
  border: 1.5px solid var(--sp-line); color: var(--sp-faint) !important; box-sizing: border-box; background: var(--sp-page); }
.ob-steps li.now .n { background: var(--bs-grad); border-color: transparent; color: #fff !important; box-shadow: 0 0 0 5px var(--sp-pickbg); }
.ob-steps li.done .n { background: var(--sp-pick); border-color: transparent; color: #fff !important; }
.ob-steps .ms { font-family: 'Material Symbols Rounded'; font-size: 18px; font-weight: normal; color: #fff !important; }
.ob-steps .t { font-weight: 600; font-size: .98rem; line-height: 30px; }
.ob-steps li:not(.now):not(.done) .t { color: var(--sp-faint) !important; font-weight: 500; }
.ob-steps .a { font-size: .85rem; color: var(--sp-soft) !important; margin-top: -4px; line-height: 1.35; }
.ob-credit { font-size: .72rem; color: var(--sp-faint) !important; margin: .9rem 0 0; line-height: 1.4; }
.ob-credit a { color: var(--sp-faint) !important; text-decoration: underline; text-underline-offset: 2px; }

/* main column */
.st-key-ob-main { min-height: 100vh; box-sizing: border-box; padding: 28px clamp(32px, 6vw, 104px) 40px; gap: 0 !important; }
.st-key-ob-main > * { max-width: 620px; width: 100% !important; }
.st-key-ob-main > :first-child { margin-bottom: auto; }
.st-key-ob-main > :last-child { margin-top: auto; }
.ob-phone-only { display: none !important; }
.bs-ob-seg { display: flex; gap: 6px; margin: .2rem 0 .3rem; }
.bs-ob-seg i { flex: 1; height: 5px; border-radius: 99px; background: var(--sp-line); }
.bs-ob-seg i.on { background: var(--bs-grad); }
.bs-ob-count { font-size: .84rem; color: var(--sp-faint) !important; font-weight: 500; margin: 0 0 .7rem; }
.bs-ob-h { font-size: clamp(1.75rem, 2.6vw, 2.35rem); font-weight: 700; line-height: 1.14; letter-spacing: -.025em; margin: 0 0 .55rem; }
.bs-ob-sub { color: var(--sp-soft) !important; margin: 0 0 1.8rem; line-height: 1.55; font-size: 1.04rem; }
.bs-fade { animation: bsfade .35s ease both; }
@keyframes bsfade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.bs-ob-intro-h { font-size: clamp(2rem, 3.2vw, 2.9rem); font-weight: 700; letter-spacing: -.03em; line-height: 1.08; margin: 0 0 .7rem; }
.ob-phone-art { margin: .4rem 0 1.4rem; }
.ob-phone-art img { width: 100%; height: auto; display: block; border-radius: 18px; mix-blend-mode: var(--sp-blend); }
/* options: equal boxes on a two-column grid, same height, left-aligned. Plus when off, check when on */
.st-key-ob-chips [data-testid="stElementContainer"], .st-key-ob-chips [data-testid="stButtonGroup"] { width: 100% !important; }
.st-key-ob-chips [data-testid="stButtonGroup"] > div:last-child { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; width: 100% !important; max-width: 100% !important; }
.st-key-ob-chips button { width: 100%; min-height: 64px; height: auto; border-radius: 16px; padding: .6rem 1.1rem; justify-content: flex-start; text-align: left;
  border: 1px solid var(--sp-line); font-size: 1rem; background: transparent; }
.st-key-ob-chips button:hover { background: var(--sp-hover); border-color: var(--sp-pick); }
.st-key-ob-chips button > div, .st-key-ob-chips button [data-testid="stMarkdownContainer"] { width: 100%; display: flex; justify-content: flex-start; text-align: left; }
.st-key-ob-chips button p { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; text-align: left; line-height: 1.25; margin: 0; }
.st-key-ob-chips button { position: relative; padding-right: 3.2rem !important; }
.st-key-ob-chips button > div > span { gap: .75rem; align-items: center; }
.st-key-ob-chips button::after { content: ""; position: absolute; right: 1rem; top: 50%; transform: translateY(-50%); width: 22px; height: 22px; border-radius: 50%;
  border: 1.5px solid var(--sp-line); box-sizing: border-box; display: grid; place-items: center; font-size: 13px; font-weight: 700; color: #fff; }
.st-key-ob-chips button[data-selected="true"] { border: 2px solid var(--sp-pick) !important; background: var(--sp-pickbg) !important; font-weight: 600; }
.st-key-ob-chips button[data-selected="true"] p { color: var(--sp-ink) !important; font-weight: 600; }
.st-key-ob-chips button[data-selected="true"]::after { content: "\\2713"; background: var(--sp-pick); border-color: var(--sp-pick); }
.st-key-ob-chips button [data-testid="stIconMaterial"] { color: var(--sp-pick) !important; font-size: 22px !important; width: 22px; }
/* days: one row of big numbers */
.st-key-ob-days [data-testid="stButtonGroup"] > div:last-child { display: grid !important; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: .5rem; width: 100% !important; max-width: 100% !important; }
.st-key-ob-days [data-testid="stElementContainer"], .st-key-ob-days [data-testid="stButtonGroup"] { width: 100% !important; }
.st-key-ob-days button { width: 100%; min-height: 60px; border-radius: 14px; font-size: 1.25rem; font-weight: 600; border: 1px solid var(--sp-line); background: transparent; justify-content: center; }
.st-key-ob-days button:hover { background: var(--sp-hover); border-color: var(--sp-pick); }
.st-key-ob-days button[data-selected="true"] { background: var(--bs-grad); border-color: transparent; }
.st-key-ob-days button[data-selected="true"] p { color: #fff !important; }
.bs-ob-days-note { margin-top: 1.1rem; font-size: 1.05rem; }
/* pick one: full-width rows with a description */
.st-key-ob-rows [data-testid="stRadio"], .st-key-ob-rows [data-testid="stRadio"] > div, .st-key-ob-rows [role="radiogroup"] { width: 100%; }
.st-key-ob-rows [data-testid="stElementContainer"] { width: 100% !important; }
.st-key-ob-rows [data-testid="stRadio"] [role="radiogroup"] { gap: .75rem; display: flex; flex-direction: column; align-items: stretch; }
.st-key-ob-rows [data-testid="stRadio"] label { width: 100%; box-sizing: border-box; align-items: flex-start; padding: 1rem 1.1rem; border: 1px solid var(--sp-line); border-radius: 14px; }
.st-key-ob-rows [data-testid="stRadio"] label:hover { background: var(--sp-hover); }
.st-key-ob-rows [data-testid="stRadio"] label:has(input:checked) { border: 2px solid var(--sp-pick); background: var(--sp-pickbg); }
.st-key-ob-foot { padding: .6rem 0 0; margin-top: 2rem; max-width: 340px; }
.st-key-ob-foot button[kind="primary"] { height: 54px; border-radius: 999px; font-weight: 600; box-shadow: 0 8px 22px rgba(192,38,211,.25); }
.st-key-ob-foot button[kind="tertiary"] p { color: var(--sp-soft) !important; }
.st-key-keep-ob-top button[kind="tertiary"] p { color: var(--sp-soft) !important; font-weight: 500; }
.ob-sum { margin: 0 0 .4rem !important; padding: 0 !important; list-style: none; }
.ob-sum li, .ob-steps li { margin: 0 !important; }
.ob-steps { padding: 0 !important; }
.ob-sum li { display: grid; grid-template-columns: 7.5rem 1fr; gap: 1rem; padding: .85rem 0; border-bottom: 1px solid var(--sp-line); }
.ob-sum li b { font-weight: 600; }
.ob-sum li span { color: var(--sp-soft) !important; }
.ob-note { font-size: .88rem; color: var(--sp-faint) !important; margin: .8rem 0 0; }
.ob-end { height: 1px; }
@media (prefers-reduced-motion: reduce) { .bs-fade { animation: none; } }

/* phone and tablet: one column, no side panel, progress bar on top */
@media (max-width: 899px) {
  .st-key-ob-shell { grid-template-columns: minmax(0, 1fr); min-height: 0; }
  .st-key-ob-shell > [data-testid="stLayoutWrapper"]:has(.st-key-ob-side) { display: none !important; }
  .st-key-ob-main { min-height: 100vh; padding: 14px 20px 28px; align-items: center; }
  .st-key-ob-main > * { max-width: 560px; }
  .st-key-ob-main > :first-child { margin-bottom: 0; }
  .ob-phone-only { display: block !important; }
  .ob-desk-only { display: none !important; }
  .st-key-ob-foot { max-width: none; position: sticky; bottom: 0; background: var(--sp-page); padding-bottom: 1rem; }
  .bs-ob-count { margin-bottom: 1.2rem; }
  .st-key-ob-chips [data-testid="stButtonGroup"] > div:last-child { grid-template-columns: minmax(0, 1fr); gap: .6rem; }
  .st-key-ob-chips button { min-height: 58px; }
}
@media (min-width: 900px) { .bs-ob-seg { display: none; } }
</style>
"""


def done(settings):
    return bool(settings.get("onboarded"))


def _data():
    return st.session_state.setdefault("ob_data", {"days": 3})


def _label(t):
    icon = GOAL_ICON.get(t)
    t = t.replace("-", "\u2011")
    return f":material/{icon}: {t}" if icon else t


def _seg(step):
    segs = "".join(f'<i class="{"on" if i <= step else ""}"></i>' for i in range(len(STEPS)))
    st.html(f'<div class="bs-ob-seg" role="img" aria-label="Step {step + 1} of {len(STEPS)}">{segs}</div>'
            f'<div class="bs-ob-count">Step {step + 1} of {len(STEPS)}</div>')


def _answer(key, d, ladders=None):
    v = d.get(key)
    if key == "days":
        return f"{int(v)} day{'s' if int(v) != 1 else ''} a week" if v else ""
    if isinstance(v, list):
        return ", ".join(v) if v else "None picked"
    return v or "Not set"


def _side(current, answers, kicker="Your first week"):
    """Laptop only: the five steps on a line, ticked as you go with your answer under each. No picture: it had no link to the step."""
    rows = []
    for i, (key, _, _) in enumerate(STEPS):
        state = "done" if i < current else "now" if i == current else ""
        mark = '<span class="ms">check</span>' if state == "done" else str(i + 1)
        ans = f'<div class="a">{html.escape(_answer(key, answers))}</div>' if state == "done" else ""
        rows.append(f'<li class="{state}"><span class="n">{mark}</span><div><div class="t">{SIDE_LABEL[key]}</div>{ans}</div></li>')
    with st.container(key="ob-side"):
        st.html(f'<img class="ob-logo" src="/app/static/logo.svg" alt="BodySync"><div class="ob-kick">{kicker}</div>'
                f'<ol class="ob-steps" aria-label="Setup steps">{"".join(rows)}</ol>')


def _css():
    st.session_state["_focus_mode"] = True
    st.html(f"<style>{ui.split_vars()}</style>")
    st.markdown(CSS, unsafe_allow_html=True)


def _set(key, value):
    _data()[key] = value


def _input(key, ladders):
    d = _data()
    if key in ("goals", "skills", "area"):
        options = (GOALS if key == "goals" else AREAS if key == "area"
                   else [l["title"] for i, l in ladders.items() if i not in ONBOARD_HIDE] + [CREATE_OWN])
        with st.container(key="ob-chips"):
            d[key] = st.pills(key, options, selection_mode="multi", default=d.get(key), key=f"ob_w_{key}",
                              format_func=_label, label_visibility="collapsed") or []
    elif key == "days":
        with st.container(key="ob-days"):
            d[key] = st.pills("Days", [1, 2, 3, 4, 5, 6, 7], default=d.get(key, 3), key=f"ob_w_{key}",
                              label_visibility="collapsed") or d.get(key, 3)
        n = int(d[key])
        st.html(f'<div class="bs-ob-days-note"><b>{n} day{"s" if n != 1 else ""} a week.</b> '
                f'{"Great for starting out." if n <= 3 else "A solid routine." if n <= 5 else "Plan a lighter day or two."}</div>')
    else:
        with st.container(key="ob-rows"):
            cur = d.get(key) if d.get(key) in LEVELS else None
            pick = st.radio("Level", LEVELS, index=LEVELS.index(cur) if cur else None, key=f"ob_w_{key}",
                            format_func=lambda l: f"**{l}**  \n{LEVEL_NOTE[l]}", label_visibility="collapsed")
            if pick:
                d[key] = pick


def _finish(username, ladders):
    d = _data()
    goals, picked = d.get("goals") or [], d.get("skills") or []
    ids = [i for i, l in ladders.items() if l["title"] in picked]
    focus = next((FOCUS_OF[g] for g in GOALS if g in goals), "explore")
    if ids and "Learn a skill" not in goals:
        focus = "skills"
    session_data.save_settings(
        username, onboarded=True, focus=focus, goals=goals, priority_skills=ids,
        weekly_goal=int(d.get("days") or 3), injury_areas=d.get("area") or [],
    )
    if ids:
        state = dict(session_data.skills(username))
        for i in ids:
            state.setdefault(i, sk.new_state(0, date.today().isoformat()))
        session_data.save_skills(username, state)
    if d.get("level"):
        p = session_data.profile(username) or {}
        session_data.save_profile(username, p.get("age"), p.get("weight"), p.get("height"), d["level"],
                                  p.get("health_condition") or "")
    for k in ("ob_step", "ob_data", "ob_replay", "ob_started"):
        st.session_state.pop(k, None)
    st.session_state["ob_welcome"] = True


def _go(step):
    st.session_state["ob_step"] = step


def _start():
    st.session_state["ob_started"] = True


ROTATING = ["strength", "routine", "pace", "skills", "plan"]
INTRO_CSS = """<style>
/* the welcome: picture, then the headline in the middle, then the buttons at the bottom */
.st-key-ob-intro { gap: 0 !important; }
.bs-rot { display: inline-grid; }
.bs-rot span { grid-area: 1 / 1; opacity: 0; animation: bsWord 12.5s infinite, bsShine 3s linear infinite;
  background: linear-gradient(90deg, #7c3aed, #c026d3, #db2777, #a855f7, #7c3aed); background-size: 220% 100%;
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.bs-rot span:nth-child(2) { animation-delay: 2.5s, 0s; } .bs-rot span:nth-child(3) { animation-delay: 5s, 0s; }
.bs-rot span:nth-child(4) { animation-delay: 7.5s, 0s; } .bs-rot span:nth-child(5) { animation-delay: 10s, 0s; }
@keyframes bsWord { 0% { opacity: 0; transform: translateY(.25em); } 3% { opacity: 1; transform: none; }
  18% { opacity: 1; transform: none; } 21% { opacity: 0; transform: translateY(-.25em); } 100% { opacity: 0; } }
@keyframes bsShine { from { background-position: 100% 0; } to { background-position: -120% 0; } }
.st-key-ob-foot button[kind="primary"] { animation: bsGlow 3.2s ease-in-out infinite; }
@keyframes bsGlow { 0%, 70%, 100% { box-shadow: 0 8px 22px rgba(192,38,211,.25); }
  85% { box-shadow: 0 0 0 6px rgba(168,85,247,.22), 0 10px 34px rgba(192,38,211,.55); } }
@media (max-width: 899px) {
  .st-key-ob-intro { min-height: calc(100dvh - 24px); display: flex; flex-direction: column; }
  .st-key-ob-intro .ob-phone-art { margin-top: 2.2rem; }
  .st-key-ob-intro > :first-child { margin-top: auto; }          /* the picture sits lower */
  .st-key-ob-intro > .stElementContainer:has(.bs-ob-intro-h) { margin-top: 1.2rem; }
  .st-key-ob-intro .bs-ob-intro-h { text-align: center; }
  .st-key-ob-intro .bs-ob-sub { text-align: center; }
  .st-key-ob-intro > [data-testid="stLayoutWrapper"]:has(.st-key-ob-foot) { margin-top: auto; }  /* buttons at the bottom */
}
@media (prefers-reduced-motion: reduce) {
  .bs-rot span, .st-key-ob-foot button[kind="primary"] { animation: none; }
  .bs-rot span:first-child { opacity: 1; }
}
</style>"""


def _intro():
    st.html(INTRO_CSS)
    with st.container(key="ob-intro"):
        st.html(f'<div class="ob-phone-only ob-phone-art bs-fade"><img src="{ui.ART}outdoor.jpg" alt=""></div>')
        words = "".join(f"<span>{w}</span>" for w in ROTATING)
        st.html(f'<div class="bs-ob-intro-h bs-fade">Build your own<br><span class="bs-rot" aria-label="strength">{words}'
                '</span></div>')
        st.html('<p class="bs-ob-sub">Five quick questions, about a minute. They set up your first week, '
                'and you can change every answer later in You.</p>')
        with st.container(key="ob-foot"):
            st.button("Get started", type="primary", key="ob_start", width="stretch", on_click=_start)
            if st.button("Skip setup", type="tertiary", key="ob_skip_all", width="stretch"):
                session_data.save_settings(st.session_state.get("ob_user", ""), onboarded=True)
                _start()
                for k in ("ob_step", "ob_data", "ob_replay"):
                    st.session_state.pop(k, None)
                st.rerun()


WELCOME_CSS = """<style>
.st-key-ob-tiles [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 12px !important; }
.st-key-ob-tiles [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; position: relative; }
.st-key-ob-tiles [data-testid="stElementContainer"]:has(.stButton) { position: absolute; inset: 0; z-index: 2; margin: 0; width: 100% !important; height: 100% !important; }
.st-key-ob-tiles .stButton, .st-key-ob-tiles .stButton button { position: absolute; inset: 0; width: 100% !important; height: 100% !important; opacity: 0; max-width: none !important; }
.st-key-ob-tiles [data-testid="stColumn"]:has(button:focus-visible) .ob-ft { outline: 3px solid var(--sp-pick); outline-offset: 2px; }
.ob-ft { border-radius: 18px; }
.ob-ft .v { aspect-ratio: 1; border-radius: 18px; overflow: hidden; background: var(--sp-pickbg); display: grid; place-items: center; }
.ob-ft .v img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ob-ft .t { font-weight: 600; margin-top: .5rem; color: var(--sp-ink); }
.ob-ft .d { font-size: .82rem; color: var(--sp-soft); margin-top: .1rem; }
.ob-week { display: flex; gap: 5px; }
.ob-week i { width: 15px; height: 34px; border-radius: 8px; background: rgba(139,92,246,.18); }
.ob-week i.on { background: linear-gradient(180deg, #ec4899, #8b5cf6); }
.ob-bars { display: flex; align-items: flex-end; gap: 7px; height: 56%; }
.ob-bars i { width: 16px; border-radius: 6px 6px 3px 3px; background: linear-gradient(180deg, #ec4899, #8b5cf6); }
</style>"""


def _feature_tiles(username, pages, settings, ladders):
    """What you can do here, shown with pictures. Each tile opens that part of the app (nothing starts by surprise)."""
    import today
    from exercise_data import find_exercise, mini_url

    def leave(**state):
        st.session_state["ob_welcome"] = False
        st.session_state.update(state)

    def pic(name):
        ex = find_exercise(name)
        return mini_url(ex) if ex else ""

    starter = next((w for w in today.curated() if w["id"] == "full-bodyweight"), None)
    lad = next((ladders[i] for i in settings.get("priority_skills", []) if i in ladders), None)
    skill_pic = pic(next((x["library"] for x in reversed(lad["steps"]) if x.get("library")), "Pushups")) if lad else pic("Pushups")
    days = SPREAD_FOR_TILE.get(int(settings.get("weekly_goal", 3)), [0, 2, 4])
    tiles = [
        ("wk", f'<img src="{html.escape(pic(starter["exercises"][0][0]) if starter else "")}" alt="">',
         "Your first workout", f"Full body · {today.workout_minutes(starter)} min" if starter else "Ready when you are"),
        ("plan", '<div class="ob-week">' + "".join(f'<i class="{"on" if d in days else ""}"></i>' for d in range(7)) + "</div>",
         "Plan your week", "Pick your days"),
        ("sk", f'<img src="{html.escape(skill_pic)}" alt="">', lad["title"] if lad else "Learn a skill",
         "Step by step" if lad else "Push-ups, splits and more"),
        ("pg", '<div class="ob-bars">' + "".join(f'<i style="height:{h}%"></i>' for h in (30, 45, 40, 62, 75, 100)) + "</div>",
         "See your progress", "Every lift and step"),
    ]
    st.html(WELCOME_CSS)
    with st.container(key="ob-tiles"):
        for row in (tiles[:2], tiles[2:]):
            cols = st.columns(2)
            for col, (k, visual, title, desc) in zip(cols, row):
                col.html(f'<div class="ob-ft"><div class="v">{visual}</div><div class="t">{html.escape(title)}</div>'
                         f'<div class="d">{html.escape(desc)}</div></div>')
                if col.button(title, key=f"ob_tile_{k}"):
                    if k == "wk" and starter:
                        leave(t_phase="template", t_tpl=starter["id"], t_tpl_from="home")
                        ui.to_workout(pages)
                    elif k == "plan":
                        leave(t_phase="plan")
                        ui.to_workout(pages)
                    elif k == "sk":  # your skill in progress, or Explore (where Create your own is first)
                        leave(sk_tab_next=1 if lad else 0)
                        st.switch_page(pages["skills"])
                    else:
                        leave()
                        st.switch_page(pages["progress"])
            st.write("")
    with st.container(key="ob-foot"):
        if st.button("Go to Home", type="primary", icon=":material/arrow_forward:", key="ob_go", width="stretch"):
            leave()
            st.rerun()


SPREAD_FOR_TILE = {1: [2], 2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 2, 4, 5], 6: [0, 1, 2, 3, 4, 5], 7: list(range(7))}


def welcome(username, pages, settings, ladders):
    _css()
    goals = settings.get("goals") or []
    skills = [ladders[i]["title"] for i in settings.get("priority_skills", []) if i in ladders]
    level = (session_data.profile(username) or {}).get("fitness_level") or ""
    answers = {"goals": goals, "skills": skills, "days": settings.get("weekly_goal", 3),
               "level": level if level in LEVELS else "", "area": settings.get("injury_areas") or []}
    name = st.session_state.get("display", "")
    with st.container(key="ob-shell"):
        with st.container(key="ob-main"):
            st.html('<div class="ob-end"></div>')
            st.html(f'<div class="bs-ob-intro-h bs-fade">{html.escape("You're set, " + name if name else "You're set")}</div>')
            st.html('<p class="bs-ob-sub">Here\'s what you can do. Tap any of them to look around.</p>')
            _feature_tiles(username, pages, settings, ladders)
            st.html('<div class="ob-end"></div>')
        _side(len(STEPS), answers, kicker="All set")


def onboarding(username, pages, settings):
    ladders = sk.ladders()
    st.session_state["ob_user"] = username
    if st.session_state.get("ob_welcome"):
        welcome(username, pages, settings, ladders)
        return
    _css()
    started = st.session_state.get("ob_started")
    step = int(st.session_state.get("ob_step", 0))
    with st.container(key="ob-shell"):
        with st.container(key="ob-main"):
            if not started:
                st.html('<div class="ob-end"></div>')
                _intro()
                st.html('<div class="ob-end"></div>')
            else:
                _question(username, ladders, step)
        if not started:
            _side(-1, {}, kicker="Five quick questions")
        else:
            _side(step, _data())


def _question(username, ladders, step):
    key, title, sub = STEPS[step]
    last = step == len(STEPS) - 1
    with st.container(key="keep-ob-top"):
        back, _, skip = st.columns([1, 5, 2])
        if step:
            back.button("", icon=":material/arrow_back:", key="ob_back", type="tertiary", help="Back", on_click=_go, args=(step - 1,))
        else:
            back.button("", icon=":material/arrow_back:", key="ob_back0", type="tertiary", help="Back to the start",
                        on_click=lambda: st.session_state.update(ob_started=False))
        if skip.button("Skip", type="tertiary", key="ob_skip", width="stretch"):
            _data().pop(key, None)
            if last:
                _finish(username, ladders)
            else:
                _go(step + 1)
            st.rerun()
    with st.container(key="ob-q"):
        _seg(step)
        st.html(f'<div class="bs-ob-h bs-fade">{title}</div>')
        st.html(f'<p class="bs-ob-sub bs-fade">{sub}</p>')
        _input(key, ladders)
        with st.container(key="ob-foot"):
            if st.button("Finish" if last else "Continue", type="primary", key="ob_next", width="stretch"):
                if last:
                    _finish(username, ladders)
                else:
                    _go(step + 1)
                st.rerun()
    st.html('<div class="ob-end"></div>')
