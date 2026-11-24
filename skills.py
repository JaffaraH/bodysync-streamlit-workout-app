"""Skills: work toward things you can't do yet (first push-up, pull-up, splits...).

Page types (docs/DESIGN.md): a step ladder per skill with the current step enlarged; a guided practice
that runs like a workout (warm-up, then the drills that build the skill, then your step, one set at a
time, with a hold timer and short rests); and an editor to create your own skill with your own steps,
drills and pictures. Level-up rule: hit the target on every set in two practices in a row. No popovers,
no expanders: every option is a visible button or a dialog.
"""
import base64
import io
import time
import uuid
from datetime import date, datetime

import html

import streamlit as st

import celebration
import research
import session_data
import training
import skill_media
import skills_logic as sk
import ui
from exercise_data import exercise_gif, find_exercise, mini_url

EVENTS = {
    "complete": ("big", "Goal reached"),
    "level_up": ("big", "Level up"),
    "clear": ("pr", "Target hit"),
    "miss": ("none", "Practice logged"),
}
REST = 45  # seconds between sets of a bodyweight skill step (short: these are low-load sets)
KINDS = {"Reps": "reps", "Seconds (hold)": "hold"}
KIND_LABEL = {v: k for k, v in KINDS.items()}
GENERIC_WARMUP = [{"name": "Easy movement", "how": "2 minutes of marching, arm circles and gentle swings to get warm."}]

CSS = """<style>
.sk-now { font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; opacity: .6; font-weight: 600; margin: .9rem 0 .15rem; }
.sk-step { font-size: 1.5rem; font-weight: 700; letter-spacing: -.02em; line-height: 1.15; margin: 0 0 .25rem; }
.sk-target { font-size: 1.05rem; margin: 0 0 .35rem; }
.sk-target b { font-size: 1.2rem; }
.sk-clock { text-align: center; font-variant-numeric: tabular-nums; padding: .4rem 0 .2rem; }
.sk-clock .n { font-size: 3.6rem; font-weight: 800; letter-spacing: -.03em; line-height: 1;
  background: var(--bs-grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
.sk-clock .l { opacity: .7; margin-top: .25rem; }
.sk-bar { height: 8px; border-radius: 99px; background: rgba(139,92,246,.16); overflow: hidden; margin: .6rem 0 .2rem; }
.sk-bar i { display: block; height: 100%; background: var(--bs-grad); border-radius: 99px; }
.st-key-sk-rows [data-testid="stRadio"] label { width: 100%; box-sizing: border-box; padding: .85rem 1rem;
  border: 1px solid rgba(139,92,246,.22); border-radius: 14px; }
.st-key-sk-rows [role="radiogroup"] { gap: .6rem; display: flex; flex-direction: column; align-items: stretch; }
.st-key-sk-rows [data-testid="stElementContainer"], .st-key-sk-rows [data-testid="stRadio"], .st-key-sk-rows [data-testid="stRadio"] > div,
.st-key-sk-rows [role="radiogroup"] { width: 100% !important; }
.st-key-sk-rows [data-testid="stRadio"] label:has(input:checked) { border: 2px solid #7c3aed; background: rgba(124,58,237,.10); }
[class*="st-key-sk-sec-"] { padding: .4rem 0 1.2rem; border-bottom: 1px solid rgba(139,92,246,.16); margin-bottom: .6rem; }
[class*="st-key-bs-pair-sk-"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .5rem; }
[class*="st-key-bs-pair-sk-"] [data-testid="stColumn"] { min-width: 0 !important; }
</style>"""


# ---------------------------------------------------------------------------------------------
# data helpers
def _ladders(username):
    return sk.all_ladders(session_data.custom_skills(username))


def _image_bytes(data_uri):
    try:
        return base64.b64decode(data_uri.split(",", 1)[1])
    except Exception:
        return None


def _shrink(upload, size=720):
    """Your own picture, resized to a phone-friendly WebP so it fits in your private storage."""
    from PIL import Image

    im = Image.open(upload).convert("RGB")
    im.thumbnail((size, size))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=72)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def _media(item, lad=None):
    """Picture for a step or drill: your own photo, a hand-picked clip, the library demo, then the skill cover."""
    if item.get("photo"):
        return ("bytes", _image_bytes(item["photo"]))
    mine = skill_media.clip(item) if item.get("id") and not (lad or {}).get("custom") else None
    if mine:
        return ("url", mine)
    ex = find_exercise(item["library"]) if item.get("library") else None
    gif = exercise_gif(ex) if ex else None
    if gif:
        return ("url", gif)
    if lad and lad.get("photo"):
        return ("bytes", _image_bytes(lad["photo"]))
    return None


def _show_media(m):
    if not m or not m[1]:
        return
    kind, val = m
    if kind == "url" and val.endswith(".mp4"):
        st.video(val.replace("/app/static/", "static/"), loop=True, muted=True, autoplay=True)
    elif kind == "url":
        ui.demo(val)
    else:
        st.image(val, width="stretch")


def _cover_url(lad):
    if lad.get("photo"):
        return lad["photo"]
    name = next((x["library"] for x in reversed(lad["steps"]) if x.get("library")), None)
    ex = find_exercise(name) if name else None
    return mini_url(ex) if ex else None


def _unit(item):
    return "s" if item.get("kind") == "hold" else "reps"


def _target_text(item):
    side = " per side" if item.get("per_side") else ""
    if item.get("kind") == "hold":
        return f"{item['sets']} × {item['target']} s hold{side}"
    return f"{item['sets']} × {item['target']} reps{side}"


# ---------------------------------------------------------------------------------------------
# the page
def skills_page(username, pages):
    result = st.session_state.pop("sk_result", None)
    if result:
        show_result(result, pages)
    st.html(CSS)
    ladders = _ladders(username)

    if st.session_state.get("skp") and st.session_state["skp"]["lid"] in ladders:
        practice_view(username, ladders[st.session_state["skp"]["lid"]])
        return
    view = st.session_state.get("sk_view")
    if view and view[0] == "about" and view[1] in ladders:
        about_view(username, ladders[view[1]])
        return
    if view and view[0] == "place" and view[1] in ladders:
        placement_view(username, ladders[view[1]])
        return
    if view and view[0] in ("create", "edit"):
        editor_view(username, ladders.get(view[1]) if view[0] == "edit" else None)
        return

    if view and view[0] == "skill" and view[1] in ladders:
        skill_detail(username, ladders[view[1]])
        return
    if view and view[0] == "move" and view[1] in ladders:
        move_view(username, ladders[view[1]])
        return

    st.title("Skills")
    st.caption(f"Work toward things you can't do yet, one step at a time. Hit the target in {sk.CLEARS_NEEDED} "
               "practices in a row and you move up.")
    state = {k: v for k, v in session_data.skills(username).items() if k in ladders}
    active = {k: v for k, v in state.items() if not v.get("done")}
    done = {k: v for k, v in state.items() if v.get("done")}
    tabs = ["Explore", f"In progress ({len(active)})", f"Done ({len(done)})"]
    want = st.session_state.pop("sk_tab_next", None)
    if want is not None:
        st.session_state["sk_tab"] = tabs[want]
    if st.session_state.get("sk_tab") not in tabs:
        st.session_state["sk_tab"] = tabs[1] if active else tabs[0]
    tab = st.segmented_control("Show", tabs, key="sk_tab", label_visibility="collapsed") or tabs[0]
    st.write("")
    if tab.startswith("Explore"):
        _explore(ladders, state)
    elif tab.startswith("In progress"):
        if not active:
            st.caption("Nothing in progress yet. Pick one in Explore, or make your own.")
        for lid, gs in active.items():
            _skill_row(username, ladders[lid], gs)
    else:
        if not done:
            st.caption("Finished skills land here, so you can see how far you've come.")
        for lid, gs in done.items():
            _skill_row(username, ladders[lid], gs)
    st.caption("General guidance, not medical advice. Stop if something hurts, and check with a professional if you have an injury.")


def _explore(ladders, state):
    """Skills you can add. Tap one to see what it is first; nothing starts until you choose."""
    opened, _ = ui.tap_row("sk-create", "add", "Create your own", "Your own steps, drills and pictures", icon=True)
    if opened:
        _set_view(("create", None))
        st.rerun()
    rest = [l for l in ladders.values() if l["id"] not in state]
    if not rest:
        st.caption("You've added every skill here. Make your own for anything else.")
    for lad in rest:
        extra = f" · {len(lad.get('drills') or [])} drills" if lad.get("drills") else ""
        opened, _ = ui.tap_row(f"sk-ex-{lad['id']}", _cover_url(lad), lad["title"],
                               f"{len(lad['steps'])} steps{extra}", kicker="Yours" if lad.get("custom") else "")
        if opened:
            _set_view(("about", lad["id"]))
            st.rerun()


def demo_note(item):
    """When a step borrows a similar library demo (no exact one exists), say so, so the picture and name never
    quietly disagree: 'Demo shows a similar move: Pullups'."""
    lib = item.get("library")
    if not lib or item.get("photo"):
        return ""
    def norm(t):  # "Full push-up" and "Pushups" are the same move
        t = "".join(ch for ch in t.lower().replace("full ", "") if ch.isalpha())
        return t[:-1] if t.endswith("s") else t
    a, b = norm(item["name"]), norm(lib)
    if a in b or b in a:
        return ""
    return f"Demo shows a similar move: {lib}"


def _step_pic(step, lad=None):
    ex = find_exercise(step["library"]) if step.get("library") else None
    return step.get("photo") or (mini_url(ex) if ex else None) or (_cover_url(lad) if lad else None)


def about_view(username, lad):
    """A skill before you add it: the goal, every step with its picture, and why it works."""
    import today

    st.button("Back to skills", icon=":material/arrow_back:", key="sk_ab_back", on_click=_back)
    ui.hero(f"{len(lad['steps'])} steps", lad["title"], lad.get("final") or lad.get("blurb", ""), _cover_url(lad))
    if lad.get("blurb"):
        st.write(lad["blurb"])
    st.markdown("##### The steps, easiest first")
    ui.tracklist([(_step_pic(x, lad), x["name"], _target_text(x)
                   + "".join(f"  ·  or {o['name']}" for o in (x.get("options") or []))
                   + (f"  ·  {demo_note(x)}" if demo_note(x) else "")) for x in lad["steps"]])
    if lad.get("drills"):
        st.caption("Each practice starts with: " + ", ".join(d["name"] for d in lad["drills"]) + ".")
    st.caption(f"Hit a step's target in {sk.CLEARS_NEEDED} practices in a row and you move up to the next one.")
    for rid in lad.get("research", []):
        why = research.why(rid)
        if why:
            st.caption("Why: " + why)
    st.html(today.SESSION_CSS)
    with st.container(key="bs-donebar"):
        st.button("Add to my skills", type="primary", icon=":material/add:", key="sk_ab_add", width="stretch",
                  on_click=_set_view, args=(("place", lad["id"]),))


def _skill_row(username, lad, gs):
    """One skill: where you are. Tap to open it; Start begins today's practice."""
    steps = lad["steps"]
    i = min(gs["step"], len(steps) - 1)
    detail = "Goal reached" if gs.get("done") else f"Step {i + 1} of {len(steps)}: {steps[i]['name']}"
    opened, acted = ui.tap_row(f"sk-row-{lad['id']}", _step_pic(steps[i], lad), lad["title"], detail,
                               action="Again" if gs.get("done") else "Start")
    if acted:
        start_practice(lad)
        st.rerun()
    if opened:
        _set_view(("skill", lad["id"]))
        st.rerun()


def skill_detail(username, lad):
    """Everything about one skill: the steps, your step now, change step, edit or make your own version."""
    import today

    st.button("Back to skills", icon=":material/arrow_back:", key="sk_det_back", on_click=_back)
    st.html(today.SESSION_CSS)
    gs = session_data.skills(username).get(lad["id"])
    if not gs:
        _back()
        st.rerun()
    skill_section(username, lad, gs)
    st.markdown("##### The steps")
    i = min(gs["step"], len(lad["steps"]) - 1)
    for n, s_ in enumerate(lad["steps"]):
        mark = "Done" if n < i or gs.get("done") else "Now" if n == i else ""
        st.markdown(f"{n + 1}. **{s_['name']}**  ·  {_target_text(s_)}" + (f"  :violet-badge[{mark}]" if mark == "Now" else
                                                                            f"  :green-badge[{mark}]" if mark else ""))
        for o in (s_.get("options") or []):
            st.caption(f"or {o['name']}  ·  {_target_text(o)}")
    if lad.get("drills"):
        st.caption("Drills each practice: " + ", ".join(d["name"] for d in lad["drills"]) + ".")
    st.write("")
    if not lad.get("custom"):
        st.caption("Want different steps, extra drills or your own pictures? Make your own version: you keep your place.")
        if st.button("Make my own version", icon=":material/content_copy:", key="sk_det_copy"):
            _own_version(username, lad, gs)
    if st.button("Remove this skill", icon=":material/delete:", key="sk_det_rm", type="tertiary"):
        _remove_dialog(username, lad)
    with st.container(key="bs-donebar"):
        st.button("Practise again" if gs.get("done") else "Start practice", type="primary", icon=":material/play_arrow:",
                  key="sk_det_go", width="stretch", on_click=start_practice, args=(lad,))


def _own_version(username, lad, gs):
    """Copy a built-in ladder into your own skills (same step), then open the editor on it."""
    custom = dict(session_data.custom_skills(username))
    new_id = f"{lad['id']}-mine-{uuid.uuid4().hex[:4]}"
    custom[new_id] = {**{k: v for k, v in lad.items() if k != "research"}, "id": new_id,
                      "title": f"{lad['title']} (my version)", "custom": True}
    session_data.save_custom_skills(username, custom)
    state = dict(session_data.skills(username))
    state[new_id] = dict(gs)
    state.pop(lad["id"], None)
    session_data.save_skills(username, state)
    st.session_state.pop("sk_draft", None)
    _set_view(("edit", new_id))
    st.rerun()


def move_view(username, lad):
    """Change step as its own screen (the pop-up was cut off on phones)."""
    gs = session_data.skills(username).get(lad["id"]) or sk.new_state()
    st.button("Back", icon=":material/arrow_back:", key="sk_mv_back", on_click=_set_view, args=(("skill", lad["id"]),))
    st.title("Change step")
    st.caption("Pick the step that matches what you can do cleanly today. Your logged practice is kept.")
    names = [s_["name"] for s_ in lad["steps"]]
    with st.container(key="sk-rows"):
        picked = st.radio("Step", list(range(len(names))), index=min(gs["step"], len(names) - 1),
                          key=f"sk_movepick_{lad['id']}", label_visibility="collapsed",
                          format_func=lambda n: f"**{n + 1}. {names[n]}**  \n{_target_text(lad['steps'][n])}")
    st.html(CSS)
    with st.container(key="bs-donebar"):
        if st.button("Move to this step", type="primary", width="stretch", key=f"sk_moveok_{lad['id']}"):
            state = session_data.skills(username)
            state[lad["id"]] = sk.new_state(int(picked), gs.get("started"))
            session_data.save_skills(username, state)
            st.toast("Step updated", icon=":material/check_circle:")
            _set_view(("skill", lad["id"]))
            st.rerun()


def _set_view(view):
    st.session_state["sk_view"] = view


def _back():
    st.session_state.pop("sk_view", None)


def skill_section(username, lad, gs):
    steps = lad["steps"]
    i = min(gs["step"], len(steps) - 1)
    step = steps[i]
    with st.container(key=f"sk-sec-{lad['id']}"):
        ui.card_header(lad["title"], f"Step {i + 1} of {len(steps)}" if not gs.get("done") else "Complete",
                       "Your skill" if lad.get("custom") else None)
        ui.stepper(len(steps), i, bool(gs.get("done")))
        if gs.get("done"):
            st.markdown(f"**Goal reached.** {lad.get('final', '')}")
            st.caption("Keep it sharp with a practice now and then, or move back to any step.")
        else:
            text, demo = st.columns([1.5, 1], vertical_alignment="top")
            with text:
                st.html(f'<div class="sk-now">Your step now</div><div class="sk-step">{html.escape(str(step["name"]))}</div>'
                        f'<div class="sk-target">Target <b>{_target_text(step)}</b></div>')
                if step.get("how"):
                    st.caption(step["how"])
                if step.get("options"):
                    st.caption("Also counts: " + ", ".join(f"{o['name']} ({_target_text(o)})" for o in step["options"]) + ".")
                if gs.get("streak"):
                    nxt = steps[min(i + 1, len(steps) - 1)]["name"]
                    st.caption(f"One clean practice so far. One more and you move up to {nxt}.")
                elif i + 1 < len(steps):
                    st.caption(f"Next step: {steps[i + 1]['name']}")
                if lad.get("drills"):
                    st.caption(f"Each practice starts with {len(lad['drills'])} drills: "
                               + ", ".join(d["name"] for d in lad["drills"]) + ".")
            with demo:
                _show_media(_media(step, lad))
        with st.container(key=f"keep-skmove-{lad['id']}"):
            a, b = st.columns(2)
            a.button("Change step", icon=":material/swap_vert:", key=f"sk_move_{lad['id']}", width="stretch",
                     on_click=_set_view, args=(("move", lad["id"]),))
            if lad.get("custom"):
                b.button("Edit steps", icon=":material/edit:", key=f"sk_more_{lad['id']}", width="stretch",
                         on_click=_set_view, args=(("edit", lad["id"]),))


@st.dialog("Change step")
def _move_dialog(username, lad, gs):
    st.write("Pick the step that matches what you can do cleanly today. Your logged practice is kept.")
    names = [s["name"] for s in lad["steps"]]
    picked = st.radio("Step", names, index=min(gs["step"], len(names) - 1), key=f"sk_movepick_{lad['id']}",
                      format_func=lambda n: f"{names.index(n) + 1}. {n}", label_visibility="collapsed")
    if st.button("Move to this step", type="primary", width="stretch", key=f"sk_moveok_{lad['id']}"):
        state = session_data.skills(username)
        state[lad["id"]] = sk.new_state(names.index(picked), gs.get("started"))
        session_data.save_skills(username, state)
        st.toast("Step updated", icon=":material/check_circle:")
        st.rerun()
    if st.button("Cancel", width="stretch", key=f"sk_movecancel_{lad['id']}"):
        st.rerun()


@st.dialog("Remove this skill?")
def _remove_dialog(username, lad):
    st.write(f"{lad['title']} leaves your skills. Your logged practice stays in Progress, and you can start it again any time.")
    if st.button("Remove", type="primary", width="stretch", key=f"sk_rmok_{lad['id']}"):
        state = session_data.skills(username)
        state.pop(lad["id"], None)
        session_data.save_skills(username, state)
        st.toast("Skill removed", icon=":material/check_circle:")
        st.rerun()
    if st.button("Keep it", width="stretch", key=f"sk_rmno_{lad['id']}"):
        st.rerun()


# ---------------------------------------------------------------------------------------------
# placement: where do you start?
def placement_view(username, lad):
    """Where are you now? Each step with its picture; tap the hardest one you can already do cleanly."""
    import today

    st.button("Back", icon=":material/arrow_back:", key="sk_place_back", on_click=_set_view, args=(("about", lad["id"]),))
    st.title("Where are you now?")
    st.caption("Tap the hardest step you can already do cleanly. Not sure? Pick step 1: you'll move up quickly if "
               "it's easy. You can change this any time.")
    key = f"sk_place_{lad['id']}"
    chosen = int(st.session_state.get(key, 0))
    for n, x in enumerate(lad["steps"]):
        alt = "".join(f" · or {o['name']}" for o in (x.get("options") or []))
        opened, _ = ui.tap_row(f"place-{lad['id']}-{n}", _step_pic(x, lad), x["name"], _target_text(x) + alt,
                               kicker=f"Step {n + 1}" + (" · chosen" if n == chosen else ""),
                               kicker_state="now" if n == chosen else "")
        if opened:
            st.session_state[key] = n
            st.rerun()
    st.html(today.SESSION_CSS)
    with st.container(key="bs-donebar"):
        if st.button(f"Start at step {chosen + 1}", type="primary", width="stretch",
                     key="sk_place_go", icon=":material/arrow_forward:"):
            state = session_data.skills(username)
            state[lad["id"]] = sk.new_state(chosen, date.today().isoformat())
            session_data.save_skills(username, state)
            st.session_state.pop(key, None)
            _set_view(("skill", lad["id"]))  # straight to your skill, with Start practice ready
            st.toast(f"{lad['title']} added to your skills", icon=":material/check_circle:")
            st.rerun()


# ---------------------------------------------------------------------------------------------
# guided practice: warm-up -> drills -> your step, one set at a time
def start_practice(lad):
    st.session_state["skp"] = {"lid": lad["id"], "stage": "warmup", "d": 0, "set": 0, "results": [],
                               "drills_done": 0, "rest_until": None, "t0": None, "held": None}
    st.session_state.pop("sk_view", None)


def _stages(lad):
    return ["warmup"] + [f"drill{n}" for n in range(len(lad.get("drills") or []))] + ["main"]


def _next_stage(lad):
    p = st.session_state["skp"]
    if p["stage"] == "warmup":
        p["stage"], p["d"], p["set"] = ("drill", 0, 0) if lad.get("drills") else ("main", 0, 0)
    elif p["stage"] == "drill":
        if p["d"] + 1 < len(lad["drills"]):
            p["d"], p["set"] = p["d"] + 1, 0
        else:
            p["stage"], p["set"] = "main", 0
    p["t0"], p["held"] = None, None


@st.fragment(run_every=1)
def _hold_clock(target):
    p = st.session_state.get("skp")
    if not p:
        return
    if p.get("t0"):
        secs = int(time.time() - p["t0"])
        label = "Target reached. Hold if you can, stop when form slips." if secs >= target else "Holding..."
    else:
        secs = int(p.get("held") or 0)
        label = "Tap Start when you are in position." if not p.get("held") else "Your time. Adjust it below if needed."
    pct = min(100, int(100 * secs / max(1, target)))
    st.html(f'<div class="sk-clock"><div class="n">{secs // 60}:{secs % 60:02d}</div><div class="l">target {target} s · {label}</div></div>'
            f'<div class="sk-bar"><i style="width:{pct}%"></i></div>')


def _start_clock():
    p = st.session_state["skp"]
    p["t0"], p["held"] = time.time(), None


def _stop_clock(key):
    p = st.session_state["skp"]
    if p.get("t0"):
        p["held"] = int(time.time() - p["t0"])
        p["t0"] = None
        st.session_state[key] = p["held"]


def _rest_skip():
    st.session_state["skp"]["rest_until"] = None


def _rest_add(s):
    p = st.session_state["skp"]
    if p.get("rest_until"):
        p["rest_until"] = max(time.time() + 5, p["rest_until"] + s)


@st.fragment(run_every=1)
def _rest_clock():
    p = st.session_state.get("skp")
    if not p or not p.get("rest_until"):
        return
    left = int(p["rest_until"] - time.time())
    if left <= 0:
        p["rest_until"] = None
        ui.ping()
        st.rerun()
    st.html(f'<div class="sk-clock"><div class="n">{left // 60}:{left % 60:02d}</div><div class="l">Rest. Shake it out and breathe.</div></div>')


def _item_screen(lad, item, label, set_no, key, on_done, args):
    """One set of one item: picture, name, target, timer (holds) or a big reps number, and a pinned Done."""
    p = st.session_state["skp"]
    left, right = st.columns([1, 1.25], vertical_alignment="top")
    with left:
        _show_media(_media(item, lad))
    with right:
        st.caption(label)
        st.html(f'<div class="sk-step">{html.escape(str(item["name"]))}</div>'
                f'<div class="sk-target">Set <b>{set_no + 1}</b> of {item["sets"]}  ·  target <b>{item["target"]} {_unit(item)}</b>'
                + (" per side" if item.get("per_side") else "") + "</div>")
        if item.get("how"):
            st.caption(item["how"])
        if demo_note(item):
            st.caption(demo_note(item))
    if key not in st.session_state:
        st.session_state[key] = int(item["target"])
    if item.get("kind") == "hold":
        _hold_clock(item["target"])
        with st.container(key="bs-rest3"):
            a, b = st.columns(2)
            a.button("Start timer", icon=":material/timer:", key=f"{key}:go", on_click=_start_clock, width="stretch",
                     disabled=bool(p.get("t0")))
            b.button("Stop", icon=":material/stop:", key=f"{key}:stop", on_click=_stop_clock, args=(key,), width="stretch",
                     disabled=not p.get("t0"))
        with st.container(key="bs-big"):
            st.number_input("Seconds held" + (" (each side)" if item.get("per_side") else ""), 0, 900, key=key, step=1)
    else:
        with st.container(key="bs-big"):
            st.number_input("Reps" + (" (each side)" if item.get("per_side") else ""), 0, 500, key=key, step=1)
    with st.container(key="bs-donebar"):
        st.button(f"Done with set {set_no + 1}", type="primary", icon=":material/check:", key=f"{key}:done",
                  on_click=on_done, args=args, width="stretch")


def _drill_done(lad, key):
    p = st.session_state["skp"]
    item = lad["drills"][p["d"]]
    p["t0"], p["held"] = None, None
    st.session_state.pop(key, None)
    if p["set"] + 1 < item["sets"]:
        p["set"] += 1
    else:
        p["drills_done"] = p.get("drills_done", 0) + 1
        _next_stage(lad)


def _main_done(lad, step, key):
    p = st.session_state["skp"]
    p["results"].append(int(st.session_state.get(key, 0) or 0))
    p["t0"], p["held"] = None, None
    st.session_state.pop(key, None)
    if p["set"] + 1 < step["sets"]:
        p["set"] += 1
        p["rest_until"] = time.time() + REST
    else:
        p["finish"] = True


@st.dialog("End this practice?")
def _end_dialog():
    p = st.session_state["skp"]
    if p["results"]:
        n = len(p["results"])
        st.write(f"You've logged {n} set{'s' if n != 1 else ''} of your step. Save them, or keep going.")
        if st.button("Save practice", type="primary", width="stretch", key="skp_end_save"):
            p["finish"] = True
            st.rerun()
    else:
        st.write("Nothing from your step is logged yet, so there's nothing to save.")
    if st.button("Keep going", width="stretch", key="skp_end_keep"):
        st.rerun()
    if st.button("Leave without saving", type="tertiary", icon=":material/close:", width="stretch", key="skp_end_quit"):
        st.session_state.pop("skp", None)
        st.rerun()


def practice_view(username, lad):
    import today  # shares the live-workout look: segmented progress, big numbers, pinned Done

    st.session_state["_focus_mode"] = True
    st.html(today.SESSION_CSS)
    p = st.session_state["skp"]
    gs = session_data.skills(username).get(lad["id"]) or sk.new_state(0)
    i = min(gs["step"], len(lad["steps"]) - 1)
    ways = sk.ways(lad["steps"][i])
    step = ways[min(int(p.get("way", 0)), len(ways) - 1)]  # the way you're doing today (the step, or an alternative)
    if p.get("finish"):
        _save_practice(username, lad, gs, step)
        return

    with st.container(key="keep-sess-top"):
        a, b = st.columns([1, 3], vertical_alignment="center")
        if a.button("End", icon=":material/close:", key="skp_end", type="tertiary"):
            _end_dialog()
        b.caption(f"{lad['title']}  ·  step {i + 1}: {step['name']}")
    stages = _stages(lad)
    cur = "warmup" if p["stage"] == "warmup" else f"drill{p['d']}" if p["stage"] == "drill" else "main"
    pos = stages.index(cur)
    st.html('<div class="bs-seg">' + "".join(f'<i class="{"done" if n < pos else "now" if n == pos else ""}"></i>'
                                              for n in range(len(stages))) + "</div>")

    if p.get("rest_until") and p["rest_until"] > time.time():
        _rest_clock()
        with st.container(key="bs-rest3"):
            c = st.columns(3)
            c[0].button("-15 s", key="skp_rm", on_click=_rest_add, args=(-15,), width="stretch")
            c[1].button("+15 s", key="skp_rp", on_click=_rest_add, args=(15,), width="stretch")
            c[2].button("Skip rest", key="skp_rs", type="primary", on_click=_rest_skip, width="stretch")
        st.caption(f"Up next: {step['name']}, set {p['set'] + 1} of {step['sets']}  ·  target {step['target']} {_unit(step)}")
        return

    if p["stage"] == "warmup":
        st.html('<div class="sk-step">Warm up</div><div class="sk-target">About 2 minutes. Easy, not tiring.</div>')
        ui.tracklist([(None, w["name"], w["how"]) for w in (lad.get("warmup") or GENERIC_WARMUP)])
        with st.container(key="bs-donebar"):
            st.button("I'm warm. Next", type="primary", icon=":material/arrow_forward:", key="skp_warm",
                      on_click=_next_stage, args=(lad,), width="stretch")
        st.button("Skip warm-up", type="tertiary", key="skp_warm_skip", on_click=_next_stage, args=(lad,))
    elif p["stage"] == "drill":
        item = lad["drills"][p["d"]]
        key = f"skp_v_{lad['id']}_d{p['d']}_{p['set']}"
        _item_screen(lad, item, f"Drill {p['d'] + 1} of {len(lad['drills'])}  ·  builds toward {step['name']}", p["set"], key,
                     _drill_done, (lad, key))
        st.button("Skip this drill", type="tertiary", key=f"skp_dskip_{p['d']}", on_click=_next_stage, args=(lad,))
    else:
        if len(ways) > 1 and not p["results"]:  # before the first set: pick today's way
            st.html('<div class="sk-now">Today\'s way</div>')
            with st.container(key="sk-rows"):
                pick = st.radio("Today's way", list(range(len(ways))), index=min(int(p.get("way", 0)), len(ways) - 1),
                                key=f"skp_way_{lad['id']}", label_visibility="collapsed",
                                format_func=lambda n: f"**{ways[n]['name']}**  \n{_target_text(ways[n])}")
            if pick != p.get("way", 0):
                p["way"] = int(pick)
                for k in [k for k in st.session_state if k.startswith(f"skp_v_{lad['id']}_m")]:
                    del st.session_state[k]  # the number box starts from the new way's target
                st.rerun()
            st.caption("Any of these counts: hit its target in {} practices in a row and you move up.".format(sk.CLEARS_NEEDED))
        key = f"skp_v_{lad['id']}_m{p['set']}"
        _item_screen(lad, step, f"Your step  ·  {sk.CLEARS_NEEDED} clean practices in a row moves you up", p["set"], key,
                     _main_done, (lad, step, key))
        if p["results"]:
            st.caption("So far: " + " · ".join(f"{r} {_unit(step)}" for r in p["results"]))
        for rid in lad.get("research", []):
            why = research.why(rid)
            if why:
                st.caption("Why: " + why)
    if lad.get("safety"):
        st.caption(lad["safety"])


def _save_practice(username, lad, gs, step):
    p = st.session_state["skp"]
    results = p["results"]
    if not results:
        st.session_state.pop("skp", None)
        st.rerun()
    name = f"Skill: {step['name']}"
    prev_best = max([s["reps"] for s in session_data.all_sets(username) if s["exercise"] == name] or [0])
    ev = sk.evaluate(step, results)
    new_gs, event = sk.advance(gs, ev["hit"], len(lad["steps"]))
    rows = [{"exercise": name, "set_no": n + 1, "weight": 0.0, "reps": r, "is_pr": False} for n, r in enumerate(results) if r > 0]
    if rows:
        session_data.log_sets(username, uuid.uuid4().hex, datetime.now().isoformat(timespec="seconds"), "skill", rows)
    state = session_data.skills(username)
    state[lad["id"]] = new_gs
    session_data.save_skills(username, state)
    st.session_state["sk_result"] = {
        "ladder": lad["title"], "step": step["name"], "event": event, "results": results, "unit": _unit(step),
        "target": _target_text(step),
        "next": lad["steps"][min(new_gs["step"] + (1 if event == "clear" else 0), len(lad["steps"]) - 1)]["name"],
        "final": lad.get("final", ""), "new_best": ev["best"] > prev_best > 0, "drills": p.get("drills_done", 0),
    }
    st.session_state.pop("skp", None)
    st.rerun()


@st.dialog("Practice saved", width="large")
def show_result(r, pages):
    tier, title = EVENTS[r["event"]]
    sub = {
        "complete": r["final"],
        "level_up": f"You're moving up to {r['next']}.",
        "clear": f"Hit it once more at this step to move up to {r['next']}.",
        "miss": f"Not at the target yet, and that's normal. Repeat this step next time and aim for {r['target']}.",
    }[r["event"]]
    badge = {"level_up": "Level up", "complete": "Done", "clear": f"1 of {sk.CLEARS_NEEDED}"}.get(r["event"])
    cards = [{"title": r["step"], "big": " · ".join(f"{x}" for x in r["results"]) + f" {r['unit']}",
              "badge": badge, "note": f"Target {r['target']}"}]
    chips = (["New best at this step"] if r["new_best"] else []) + ([f"{r['drills']} drills done"] if r.get("drills") else [])
    st.html(celebration.render(tier, title, sub, cards, chips))
    st.caption("Practise a skill 2 to 3 times a week, with a day between when you can.")
    a, b = st.columns(2)
    if a.button("Back to Skills", type="primary", width="stretch", key="skr_done"):
        st.rerun()
    if b.button("Go Home", width="stretch", key="skr_home"):
        st.switch_page(pages["home"])


# ---------------------------------------------------------------------------------------------
# create / edit your own skill: plain rows, one per step (no spreadsheet), big +/- numbers
TEMPLATE_STEPS = [{"name": "", "kind": "hold", "sets": 3, "target": 20}]
EDITOR_CSS = """<style>
[class*="st-key-skrow-"] { padding: .9rem 1rem .4rem; border: 1px solid rgba(139,92,246,.22); border-radius: 16px; margin-bottom: .7rem; }
[class*="st-key-skrow-"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .6rem; }
[class*="st-key-skrow-"] [data-testid="stColumn"] { min-width: 0 !important; }
.sk-rowh { font-weight: 700; font-size: 1rem; margin: 0; }
.sk-ladder { line-height: 1.6; opacity: .85; }
</style>"""


def _draft(lad):
    """The skill being edited, kept in the session so nothing is lost while you add or move rows."""
    d = st.session_state.get("sk_draft")
    lid = lad["id"] if lad else None
    if not d or d.get("for") != lid:
        def rows(items):
            return [{**it, "uid": uuid.uuid4().hex[:6]} for it in items]
        d = {"for": lid, "id": lid or f"custom-{uuid.uuid4().hex[:8]}",
             "steps": rows(lad["steps"] if lad else TEMPLATE_STEPS), "drills": rows((lad or {}).get("drills") or [])}
        st.session_state["sk_draft"] = d
    return d


def _add_row(group):
    st.session_state["sk_draft"][group].append({"uid": uuid.uuid4().hex[:6], "name": "", "kind": "hold" if group == "drills" else "reps",
                                                "sets": 2 if group == "drills" else 3, "target": 30 if group == "drills" else 8})


def _remove_row(group, uid):
    rows = st.session_state["sk_draft"][group]
    st.session_state["sk_draft"][group] = [r for r in rows if r["uid"] != uid]


def _move_up(group, uid):
    rows = st.session_state["sk_draft"][group]
    i = next(n for n, r in enumerate(rows) if r["uid"] == uid)
    if i > 0:
        rows[i - 1], rows[i] = rows[i], rows[i - 1]


def _row_editor(group, n, row, total):
    """One step (or drill) as a small form: name, reps or seconds, sets, target, each side, how."""
    u = row["uid"]
    label = "Step" if group == "steps" else "Drill"
    with st.container(key=f"skrow-{group}-{u}"):
        h, up, rm = st.columns([2.4, 1.3, 1.9], vertical_alignment="center")
        h.html(f'<p class="sk-rowh">{label} {n + 1}' + (" (easiest)" if group == "steps" and n == 0 and total > 1 else "")
               + (" (the goal)" if group == "steps" and n == total - 1 and total > 1 else "") + "</p>")
        up.button("Up", key=f"skup-{u}", icon=":material/arrow_upward:", type="tertiary", on_click=_move_up, args=(group, u),
                  disabled=n == 0, help="Move up")
        rm.button("Remove", key=f"skrm-{u}", icon=":material/close:", type="tertiary", on_click=_remove_row, args=(group, u),
                  disabled=group == "steps" and total == 1, help="Remove this row")
        for k, v in (("nm", row.get("name", "")), ("kd", "Seconds" if row.get("kind") == "hold" else "Reps"),
                     ("st", int(row.get("sets", 3))), ("tg", int(row.get("target", 10))), ("sd", bool(row.get("per_side"))),
                     ("hw", row.get("how", ""))):
            st.session_state.setdefault(f"sk{k}-{u}", v)
        st.text_input("Name", key=f"sknm-{u}", placeholder="e.g. Low lunge" if group == "steps" else "e.g. Hamstring stretch")
        kind = st.segmented_control("Count it in", ["Reps", "Seconds"], key=f"skkd-{u}") or "Reps"
        a, b = st.columns(2)
        a.number_input("Sets", 1, 10, key=f"skst-{u}", step=1)
        b.number_input("Seconds each set" if kind == "Seconds" else "Reps each set", 1, 900, key=f"sktg-{u}", step=5 if kind == "Seconds" else 1)
        st.toggle("Each side (left and right)", key=f"sksd-{u}")
        st.text_input("How to do it (optional)", key=f"skhw-{u}", placeholder="A short cue, like 'hips square, breathe out'")
        if group == "steps" and row.get("photo"):
            st.caption("Has your picture.")
        if group == "steps":
            st.file_uploader("Picture for this step (optional)", type=["png", "jpg", "jpeg", "webp"], key=f"skph-{u}")
            _options_editor(row)


def _options_editor(row):
    """Other ways to clear this step (for example a slow-lowering version, or a plank hold). Any one counts."""
    opts = row.setdefault("options", [])
    for o in opts:
        o.setdefault("uid", uuid.uuid4().hex[:6])
    if opts:
        st.markdown("**Other ways to clear this step**")
    for o in list(opts):
        ou = o["uid"]
        for k, v in (("nm", o.get("name", "")), ("kd", "Seconds" if o.get("kind") == "hold" else "Reps"),
                     ("st", int(o.get("sets", 3))), ("tg", int(o.get("target", 8)))):
            st.session_state.setdefault(f"sko{k}-{ou}", v)
        n, x = st.columns([6, 1], vertical_alignment="bottom")
        n.text_input("Name", key=f"skonm-{ou}", placeholder="e.g. Slow-lowering push-up")
        if x.button("", key=f"skorm-{ou}", icon=":material/delete:", type="tertiary", help="Remove this way"):
            row["options"] = [y for y in opts if y["uid"] != ou]
            st.rerun()
        kind = st.segmented_control("Count it in", ["Reps", "Seconds"], key=f"skokd-{ou}") or "Reps"
        a, b = st.columns(2)
        a.number_input("Sets", 1, 10, key=f"skost-{ou}", step=1)
        b.number_input("Seconds each set" if kind == "Seconds" else "Reps each set", 1, 900, key=f"skotg-{ou}",
                       step=5 if kind == "Seconds" else 1)
    if len(opts) < 3 and st.button("Add another way to clear this step", icon=":material/alt_route:", key=f"skoadd-{row['uid']}",
                                   type="tertiary", help="Any one of them counts toward moving up"):
        opts.append({"uid": uuid.uuid4().hex[:6], "name": "", "kind": "reps", "sets": 3, "target": 8})
        st.rerun()


def _collect_options(row):
    out = []
    for o in row.get("options") or []:
        ou = o["uid"]
        name = (st.session_state.get(f"skonm-{ou}") or "").strip()
        if not name:
            continue
        out.append({"id": o.get("id") or f"o{ou}", "name": name,
                    "kind": "hold" if st.session_state.get(f"skokd-{ou}") == "Seconds" else "reps",
                    "sets": int(st.session_state.get(f"skost-{ou}") or 1), "target": int(st.session_state.get(f"skotg-{ou}") or 1),
                    "library": o.get("library"), "how": o.get("how", "")})
    return out


def _collect(group, rows):
    out = []
    for r in rows:
        u = r["uid"]
        name = (st.session_state.get(f"sknm-{u}") or "").strip()
        if not name:
            continue
        item = {"id": r.get("id") or f"{group[0]}{u}", "name": name,
                "kind": "hold" if st.session_state.get(f"skkd-{u}") == "Seconds" else "reps",
                "sets": int(st.session_state.get(f"skst-{u}") or 1), "target": int(st.session_state.get(f"sktg-{u}") or 1),
                "per_side": bool(st.session_state.get(f"sksd-{u}")), "how": (st.session_state.get(f"skhw-{u}") or "").strip(),
                "library": r.get("library")}  # a copied built-in step keeps its exercise picture
        up = st.session_state.get(f"skph-{u}")
        if up:
            item["photo"] = _shrink(up)
        elif r.get("photo"):
            item["photo"] = r["photo"]
        if group == "steps":
            opts = _collect_options(r)
            if opts:
                item["options"] = opts
        out.append(item)
    return out


def editor_view(username, lad):
    st.html(EDITOR_CSS)
    st.button("Back", icon=":material/arrow_back:", key="sk_ed_back", on_click=_leave_editor)
    st.title("Edit your skill" if lad else "Create your own skill")
    st.caption("Three parts: a name, the steps from easiest to the goal, and (optional) drills you do every practice. "
               "You can change any of it later.")
    d = _draft(lad)
    lid = d["id"]
    st.session_state.setdefault(f"ed_t_{lid}", lad["title"] if lad else "")
    st.session_state.setdefault(f"ed_f_{lid}", lad.get("final", "") if lad else "")
    st.text_input("Skill name", key=f"ed_t_{lid}", placeholder="e.g. Middle splits")
    st.text_input("What does 'done' look like? (optional)", key=f"ed_f_{lid}", placeholder="e.g. Sit in a middle split for 30 seconds")
    photo = st.file_uploader("Cover picture (optional)", type=["png", "jpg", "jpeg", "webp"], key=f"ed_p_{lid}",
                             help="Shown on your skill. Resized and kept in your own private storage.")
    if lad and lad.get("photo") and not photo:
        st.image(_image_bytes(lad["photo"]), width=140)

    st.subheader("Steps", anchor=False)
    st.caption("Start with something you can already do, end with the goal. Reps or seconds, how many sets, and the target "
               f"for each set. Hit every set's target in {sk.CLEARS_NEEDED} practices in a row to move up.")
    for n, row in enumerate(d["steps"]):
        _row_editor("steps", n, row, len(d["steps"]))
    st.button("Add a step", icon=":material/add:", key="sk_add_step", on_click=_add_row, args=("steps",), width="stretch")

    st.subheader("Drills (optional)", anchor=False)
    st.caption("Done before your step in every practice, like the stretches that open your hips before a split.")
    for n, row in enumerate(d["drills"]):
        _row_editor("drills", n, row, len(d["drills"]))
    st.button("Add a drill", icon=":material/add:", key="sk_add_drill", on_click=_add_row, args=("drills",), width="stretch")

    names = [(st.session_state.get(f"sknm-{r['uid']}") or "").strip() for r in d["steps"]]
    if any(names):
        st.html('<p class="sk-ladder"><b>Your ladder:</b> ' + " &rarr; ".join(n or "(unnamed)" for n in names) + "</p>")
    if st.button("Save skill", type="primary", width="stretch", icon=":material/check:", key=f"ed_save_{lid}"):
        title = (st.session_state.get(f"ed_t_{lid}") or "").strip()
        steps = _collect("steps", d["steps"])
        drills = _collect("drills", d["drills"])
        if not title:
            st.error("Give your skill a name at the top.")
            return
        if not steps:
            st.error("Name at least one step.")
            return
        final = (st.session_state.get(f"ed_f_{lid}") or "").strip()
        new = {"id": lid, "custom": True, "title": title, "final": final or f"{steps[-1]['name']}, {_target_text(steps[-1])}",
               "blurb": "Your own skill", "warmup": (lad or {}).get("warmup") or GENERIC_WARMUP,
               "drills": drills, "steps": steps, "photo": _shrink(photo) if photo else (lad or {}).get("photo")}
        mine = dict(session_data.custom_skills(username))
        mine[lid] = new
        session_data.save_custom_skills(username, mine)
        if lad:  # keep your place on the ladder if steps were removed
            state = session_data.skills(username)
            if lid in state and state[lid]["step"] >= len(steps):
                state[lid] = {**state[lid], "step": len(steps) - 1, "streak": 0}
                session_data.save_skills(username, state)
        st.session_state.pop("sk_draft", None)
        st.toast("Skill saved", icon=":material/check_circle:")
        if lad:
            _back()
        else:
            _set_view(("place", lid))
        st.rerun()
    if lad and st.button("Delete this skill", type="tertiary", icon=":material/delete:", key=f"ed_del_{lid}"):
        _delete_dialog(username, lad)


def _leave_editor():
    st.session_state.pop("sk_draft", None)
    _back()


@st.dialog("Delete this skill?")
def _delete_dialog(username, lad):
    st.write(f"This deletes {lad['title']}, its steps, drills and pictures. Your logged practice stays in Progress. "
             "This can't be undone.")
    if st.button("Delete for good", type="primary", width="stretch", key="ed_del_ok"):
        mine = dict(session_data.custom_skills(username))
        mine.pop(lad["id"], None)
        session_data.save_custom_skills(username, mine)
        state = session_data.skills(username)
        state.pop(lad["id"], None)
        session_data.save_skills(username, state)
        st.session_state.pop("sk_draft", None)
        _back()
        st.toast("Skill deleted", icon=":material/delete:")
        st.rerun()
    if st.button("Keep it", width="stretch", key="ed_del_no"):
        st.rerun()
