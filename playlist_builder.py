"""New playlist, as a flow (also used to edit one):

1. Name it and pick what you want to work on (or skip).
2. Pick exercises: search, Filters, an A to Z list with pictures. Tap to add; the count follows you.
3. Your list: picture, name, sets and reps (or seconds) for each, an X to remove, Add more exercises,
   and a body map of what it works. Create it: the pictures stack in, then a tick and its name.
"""
import streamlit as st

import body_map
import exercise_picker
import session_data
import skills_logic as sk
import training
import ui
from exercise_data import find_exercise, load_exercises, prepare_minis

KEY = "pb"
PAGE = 25
AREAS = {  # what you want to work on -> the Muscle filter on step 2
    "Upper body": ["chest", "shoulders", "biceps", "triceps", "lats", "middle back", "traps"],
    "Lower body": ["quadriceps", "hamstrings", "glutes", "calves", "adductors", "abductors"],
    "Full body": [],
    "Core": ["abdominals", "lower back"],
    "Push": ["chest", "shoulders", "triceps"],
    "Pull": ["lats", "middle back", "biceps", "traps"],
    "Legs": ["quadriceps", "hamstrings", "calves"],
    "Glutes": ["glutes", "abductors", "hamstrings"],
    "Arms": ["biceps", "triceps", "forearms"],
    "Shoulders": ["shoulders", "traps"],
}
CSS = """<style>
div[class*='st-key-keep-pb-hd-'] div[data-testid='stHorizontalBlock'] > div[data-testid='stColumn']:nth-child(3){flex:1 1 auto !important}
div[class*='st-key-keep-pb-hd-'] div[data-testid='stHorizontalBlock'] > div[data-testid='stColumn']:not(:nth-child(3)){flex:0 0 auto !important;width:auto !important}
[class*='st-key-bs-mv-'] { gap: 2px !important; }
[class*='st-key-bs-mv-'] button { min-height: 26px !important; height: 26px; width: 34px; padding: 0 !important; border: none !important;
  background: transparent !important; }
[class*='st-key-bs-mv-'] button:disabled { opacity: .25; }
div[class*='st-key-keep-pb-amt-'] div[data-testid='stHorizontalBlock'] > div[data-testid='stColumn']
  {flex:1 1 0 !important;width:auto !important;max-width:none !important}
.bs-letter{font-size:.78rem;font-weight:800;letter-spacing:.08em;color:var(--bs-accent-ink);margin:14px 0 2px}
.bs-pbname{font-weight:700;line-height:1.25}.bs-pbname small{display:block;font-weight:500;opacity:.7;font-size:.82rem}
</style>"""


def _s():
    return st.session_state.setdefault(KEY, {"step": 1, "name": "", "areas": [], "picked": [], "amt": {},
                                             "skills": [], "editing": None})


def _clear():
    for k in [k for k in st.session_state if k == KEY or k.startswith(("pb_", "pk_"))]:
        del st.session_state[k]


def start(username, editing=None, picked=(), name="", amounts=None, back_to_plan=None, back_to=None):
    """Open the flow: empty, prefilled with exercises (from the Exercise library, a planned day or FitBuddy), or
    editing a playlist. back_to_plan=<day> returns to Plan my week afterwards, with this playlist on that day.
    back_to=(page, key) returns to that page and stores the saved playlist's name in st.session_state[key]."""
    _clear()
    s = _s()
    s["back_to_plan"] = back_to_plan
    s["back_to"] = back_to
    if editing:
        items = session_data.routine_items(username, editing)
        names = list(dict.fromkeys(i["workout_name"] for i in items))
        by = {i["workout_name"]: i for i in items}
        s.update(step=3, name=editing, editing=editing,
                 picked=[n for n in names if not n.startswith("Skill: ")],
                 skills=[n[7:] for n in names if n.startswith("Skill: ")],
                 amt={n: [int(by[n]["sets"] or 3), int(by[n]["reps"] or 10)] for n in names if not n.startswith("Skill: ")})
    elif picked:
        s.update(step=3, picked=list(picked), name=_free_name(username, name) if name else "",
                 amt={n: (amounts or {}).get(n) or _default(n) for n in picked})
    st.session_state["lib_view"] = ("build", editing)


def _default(name):
    return [3, 30] if training.kind_of(name) == "hold" else [3, 10]


def _go(step):
    _s()["step"] = step
    ui.to_top()


def _to_planner(day=None, key=None):
    """Back to Plan my week, on its last step (Your week), with this day's choice updated if one was saved."""
    if key:
        st.session_state[f"wp_{day}"] = key
        st.session_state.setdefault("wp_draft", {})[str(day)] = key
    st.session_state.update(t_phase="plan", wp_step=3, lib_view=None, _pb_goto_plan=True)  # lifts_page switches


def _to_page(page, key=None, name=None):
    """Back to the page this flow was opened from (FitBuddy), telling it which playlist was saved."""
    if key and name:
        st.session_state[key] = name
    st.session_state.update(lib_view=None, _pb_goto=page)  # lifts_page switches on its next run


def _leave():
    if _s().get("back_to"):
        page = _s()["back_to"][0]
        _clear()
        _to_page(page)
        return
    if _s().get("back_to_plan") is not None:
        _clear()
        _to_planner()
        return
    editing = _s().get("editing")
    _clear()
    st.session_state["lib_view"] = ("pl", editing) if editing else None
    st.session_state["lib_tab_next"] = "Playlists"


def _top(back_label, back_fn, args=()):
    """Back goes one step back; Cancel always leaves the flow (nothing is saved until you tap Create)."""
    with st.container(key="keep-pb-top"):
        a, b = st.columns(2, vertical_alignment="center")
        a.button(back_label, icon=":material/arrow_back:", key="pb_back", on_click=back_fn, args=args)
        b.button("Cancel", icon=":material/close:", key="pb_cancel", on_click=_leave, type="tertiary")


def page(username, pages):
    st.html(CSS)
    s = _s()
    {1: _step_name, 2: _step_pick, 3: _step_list}[s["step"]](username, s)


# --- 1. name and focus ----------------------------------------------------------------------------
def _step_name(username, s):
    _top("Playlists", _leave)
    ui.stepper(3, 0)
    st.title("New playlist", anchor=False)
    s["name"] = st.text_input("Name it", value=s["name"], placeholder="e.g. Leg day, Morning stretch", max_chars=40,
                              key="pb_name1")
    s["areas"] = st.pills("What do you want to work on?", list(AREAS), selection_mode="multi", default=s["areas"],
                          key="pb_areas") or []
    st.caption("Pick any, or skip if you're not sure. This only sets the filters on the next step; "
               "you can change them there.")
    import today
    st.html(today.SESSION_CSS)
    with st.container(key="bs-donebar"):
        with st.container(key="keep-pb-nav1"):
            a, b = st.columns(2)
            if a.button("Skip", key="pb_skip", width="stretch"):
                s["areas"] = []
                _to_pick(s)
            if b.button("Next", type="primary", icon=":material/arrow_forward:", icon_position="right", key="pb_next1",
                        width="stretch"):
                _to_pick(s)


def _to_pick(s):
    muscles = sorted({m for a in s["areas"] for m in AREAS[a]})
    for k in [k for k in st.session_state if k.startswith("pk_")]:  # fresh filters from the new focus
        del st.session_state[k]
    st.session_state["pk_mus"] = muscles
    s["page"] = 1
    _go(2)
    st.rerun()


# --- 2. pick exercises ------------------------------------------------------------------------------
def _step_pick(username, s):
    if s["editing"]:  # editing starts at the list, so "back" from here is the list
        _top("Your list", _go, (3,))
    else:
        _top("Back", _go, (1,))
    ui.stepper(3, 1)
    st.title("Add exercises", anchor=False)
    found, q = exercise_picker.search(username, load_exercises(), "pk")
    picked = s["picked"]
    st.caption(f"{len(found)} exercise{'s' if len(found) != 1 else ''}, A to Z. Tap to add or remove.")

    ladders = sk.all_ladders(session_data.custom_skills(username))
    mine = [lid for lid, g in session_data.skills(username).items() if lid in ladders and not g.get("done")]
    if mine and not q:
        st.markdown('<div class="bs-letter">YOUR SKILLS</div>', unsafe_allow_html=True)
        for lid in mine:
            on = lid in s["skills"]
            first = ladders[lid]["steps"][0].get("library")
            ex = find_exercise(first) if first else None
            pic = prepare_minis([ex]).get(ex["name"]) if ex else None
            opened, _ = ui.tap_row(f"pbsk-{lid}", pic, f"{ladders[lid]['title']} practice",
                                   "Drills, then your current step", end="check_circle" if on else "add_circle", end_on=on)
            if opened:
                s["skills"] = [x for x in s["skills"] if x != lid] if on else s["skills"] + [lid]
                st.rerun()

    if not found:
        ui.empty_state("No exercises match", "Try a shorter search or clear a filter.", icon="search")
    shown = found[: PAGE * s.get("page", 1)]
    minis = prepare_minis(shown)
    letter = None
    for e in shown:
        first = e["name"][:1].upper()
        if first != letter:
            letter = first
            st.markdown(f'<div class="bs-letter">{letter}</div>', unsafe_allow_html=True)
        on = e["name"] in picked
        opened, _ = ui.tap_row(f"pb-{e['id']}", minis.get(e["name"]), e["name"], exercise_picker.describe(e),
                               end="check_circle" if on else "add_circle", end_on=on)
        if opened:
            if on:
                picked.remove(e["name"])
            else:
                picked.append(e["name"])
                s["amt"].setdefault(e["name"], _default(e["name"]))
            st.rerun()
    if len(found) > len(shown):
        if st.button(f"Show more ({len(found) - len(shown)} left)", key="pb_more", icon=":material/expand_more:"):
            s["page"] = s.get("page", 1) + 1
            st.rerun()

    n = len(picked) + len(s["skills"])
    import today
    st.html(today.SESSION_CSS)
    with st.container(key="bs-donebar"):
        if st.button(f"Next · {n} selected" if n else "Pick at least one", type="primary", key="pb_next2",
                     icon=":material/arrow_forward:", icon_position="right", width="stretch", disabled=not n):
            s["from_list"] = True
            _go(3)
            st.rerun()


# --- 3. your list -------------------------------------------------------------------------------------
def _step_list(username, s):
    import today

    if s["editing"]:
        _top("Playlist", _leave)
    else:
        _top("Back", _back_to_pick, (s,))
    ui.stepper(3, 2)
    if not s["name"].strip():  # never block Create on a name: suggest one, they can change it
        s["name"] = _free_name(username, " + ".join(s["areas"]) if s["areas"] else "My playlist")
    day = s.get("back_to_plan")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    st.title(f"{days[day]}'s workout" if day is not None else "Edit playlist" if s["editing"] else "Your playlist",
             anchor=False)
    if day is not None:
        st.caption(f"Change anything. Saving keeps it as your own playlist and puts it on {days[day]}.")
    s["name"] = st.text_input("Name", value=s["name"], placeholder="e.g. Leg day", max_chars=40, key="pb_name3")
    exs = [e for e in (find_exercise(n) for n in s["picked"]) if e]
    main, also = body_map.muscles_for(exs)
    mins = today._minutes([(n, s["amt"].get(n, _default(n))[0]) for n in s["picked"]]) + 5 * len(s["skills"])
    total = len(s["picked"]) + len(s["skills"])
    st.caption(f"{total} move{'s' if total != 1 else ''}  ·  about {mins} min")
    if main:
        st.markdown(body_map.works_line(main, also))

    minis = prepare_minis(exs)
    for i, name in enumerate(list(s["picked"])):
        ex = find_exercise(name)
        sets, reps = s["amt"].setdefault(name, _default(name))
        hold = training.kind_of(name) == "hold"
        with st.container(key=f"keep-pb-hd-{i}"):
            mv, pic, nm, sw, x = st.columns([1, 1, 5, 1, 1], vertical_alignment="center")
            with mv, st.container(key=f"bs-mv-pb{i}"):  # the same reorder handle as the ready page
                st.button("", icon=":material/keyboard_arrow_up:", key=f"pb_up_{i}", help="Move up", disabled=i == 0,
                          on_click=_move, args=(s, i, -1))
                st.button("", icon=":material/keyboard_arrow_down:", key=f"pb_dn_{i}", help="Move down",
                          disabled=i == len(s["picked"]) - 1, on_click=_move, args=(s, i, 1))
            with pic:
                ui.thumb(minis[name], "sm") if minis.get(name) else ui.icon_thumb("fitness_center")
            nm.html(f'<div class="bs-pbname">{ui.html.escape(name)}'
                    f'<small>{ui.html.escape(exercise_picker.describe(ex) if ex else "")}</small></div>')
            if sw.button("", key=f"pb_sw_{i}", icon=":material/swap_horiz:", help="Swap for a similar exercise"):
                exercise_picker.swap_dialog(name, hold, s["picked"], lambda new, i=i, old=name: _swap(s, i, old, new))
            if x.button("", key=f"pb_rm_{i}", icon=":material/close:", help=f"Remove {name}"):
                s["picked"].remove(name)
                st.rerun()
        with st.container(key=f"keep-pb-amt-{i}"):
            a, b = st.columns(2)
            sets = int(a.number_input("Sets", 1, 10, int(sets), key=f"pb_s_{name}"))
            reps = int(b.number_input("Seconds" if hold else "Reps", 5 if hold else 1, 600 if hold else 100,
                                      int(reps), 5 if hold else 1, key=f"pb_r_{name}"))
            s["amt"][name] = [sets, reps]
        if i < len(s["picked"]) - 1 or s["skills"]:
            st.divider()

    ladders = sk.all_ladders(session_data.custom_skills(username))
    for lid in list(s["skills"]):
        if lid not in ladders:
            continue
        with st.container(key=f"keep-pbsk-{lid}"):
            pic, nm, x = st.columns([1, 5, 1], vertical_alignment="center")
            with pic:
                ui.icon_thumb("trending_up")
            nm.html(f'<div class="bs-pbname">{ui.html.escape(ladders[lid]["title"])} practice'
                    '<small>Drills, then your current step</small></div>')
            if x.button("", key=f"pb_rmsk_{lid}", icon=":material/close:", help="Remove"):
                s["skills"].remove(lid)
                st.rerun()
        if lid != s["skills"][-1]:
            st.divider()

    st.write("")
    st.button("Add more exercises", icon=":material/add:", key="pb_addmore", on_click=_back_to_pick, args=(s,))
    st.divider()
    clean = s["name"].strip() or _free_name(username, "My playlist")
    taken = clean in session_data.routines(username) and clean != s["editing"]
    st.html(today.SESSION_CSS)
    with st.container(key="bs-donebar"):
        if taken:
            st.caption(f"You already have a playlist called {clean}. Change the name above.")
        elif not total:
            st.caption("Add at least one exercise.")
        label = (f"Save to {days[day]}" if day is not None else "Save changes" if s["editing"] else "Create playlist")
        if st.button(label, type="primary", icon=":material/check:",
                     key="pb_save", width="stretch", disabled=not total or taken):
            _save(username, s, clean, [minis.get(n) for n in s["picked"]])


def _move(s, i, d):
    j = i + d
    if 0 <= j < len(s["picked"]):
        s["picked"][i], s["picked"][j] = s["picked"][j], s["picked"][i]


def _swap(s, i, old, new):
    """Replace one exercise in the list, keeping its sets and reps."""
    s["picked"][i] = new
    s["amt"][new] = s["amt"].pop(old, _default(new))


def _free_name(username, base):
    """'Leg day', or 'Leg day 2' if that's taken."""
    have, n, name = set(session_data.routines(username)), 2, base
    while name in have:
        name, n = f"{base} {n}", n + 1
    return name


def _back_to_pick(s):
    s["from_list"] = True
    _go(2)


def _save(username, s, name, pics):
    if s["editing"]:
        session_data.delete_routine(username, s["editing"])
    for n in s["picked"]:
        sets, reps = s["amt"].get(n, _default(n))
        session_data.add_routine(username, name, [n], int(sets), int(reps), 0)
    for lid in s["skills"]:  # a skill block: drills + your current step when it starts
        session_data.add_routine(username, name, [f"Skill: {lid}"], 0, 0, 0)
    kicker = "Changes saved" if s["editing"] else "Playlist created"
    day, back = s.get("back_to_plan"), s.get("back_to")
    _clear()
    if back:  # opened from FitBuddy: back there, with this day marked saved
        st.toast(f"Saved {name}", icon=":material/check_circle:")
        _to_page(back[0], back[1], name)
        st.rerun()
    if day is not None:  # made from a planned day: put it on that day and go back to the planner
        st.toast(f"{name} is on {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][day]}", icon=":material/check_circle:")
        _to_planner(day, f"rt:{name}")
        st.rerun()
    st.session_state["lib_view"] = ("pl", name)
    st.session_state["pl_made"] = (kicker, name, [p for p in pics if p])
    st.rerun()
