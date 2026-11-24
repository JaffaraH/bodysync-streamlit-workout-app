"""One way to find exercises, used everywhere you pick them (Exercise library, New playlist):
a search box, then Filters (Muscle, Equipment, Type, Level, Saved only). Results come back A to Z."""
import streamlit as st

import body_map
import session_data

LEVEL_ORDER = ["beginner", "intermediate", "expert"]
LEVELS_FOR = {"Beginner": ["beginner"], "Intermediate": ["beginner", "intermediate"], "Advanced": LEVEL_ORDER}
EQUIP_NAMES = {"body only": "No equipment", "kettlebells": "Kettlebell", "e-z curl bar": "EZ curl bar"}


def _equip(e):
    return e.get("equipment") or "body only"  # entries without equipment are floor moves and stretches


def _options(exercises, key):
    values = set()
    for e in exercises:
        v = _equip(e) if key == "equipment" else e.get(key)
        values.update(v if isinstance(v, list) else [v])
    return sorted(x for x in values if x)


def _label(text):
    text = EQUIP_NAMES.get(text, body_map.nice(text))
    return text[:1].upper() + text[1:]


def search(username, exercises, key, preset_muscles=None, only_with_demo=True):
    """Draw the search box and Filters; return the matching exercises sorted by name.
    preset_muscles fills the Muscle filter the first time (e.g. from 'What do you want to work on?')."""
    if preset_muscles is not None and f"{key}_mus" not in st.session_state:
        st.session_state[f"{key}_mus"] = list(preset_muscles)
    if only_with_demo:  # every exercise you can pick has a demo (your own exercises always count)
        exercises = [e for e in exercises if e.get("images")]
    from exercise_data import custom_list
    exercises = custom_list() + [e for e in exercises if not e.get("custom")]
    profile = session_data.profile(username) or {}
    active = sum(bool(st.session_state.get(f"{key}_{k}")) for k in ("mus", "eq", "cat", "lvl", "saved"))
    top = st.columns([3, 1.3], vertical_alignment="center")
    q = top[0].text_input("Search", placeholder=f"Search {len(exercises)} exercises", key=f"{key}_q",
                          label_visibility="collapsed", icon=":material/search:")
    is_open = st.session_state.get(f"{key}_open", False)
    top[1].button(f"Filters{f' · {active}' if active else ''}", icon=":material/close:" if is_open else ":material/tune:",
                  key=f"{key}_fbtn", width="stretch", on_click=_toggle, args=(key,),
                  type="primary" if is_open else "secondary")
    if is_open:  # filters open in place, with a clear way out (a pop-over hid the list on small phones)
        panel = st.container(border=True)
        with panel:
            st.multiselect("Muscle", _options(exercises, "primaryMuscles"), key=f"{key}_mus", format_func=_label)
            st.multiselect("Equipment", _options(exercises, "equipment"), key=f"{key}_eq", format_func=_label)
            st.multiselect("Type", _options(exercises, "category"), key=f"{key}_cat", format_func=_label)
            st.multiselect("Level", [l for l in LEVEL_ORDER if l in _options(exercises, "level")], key=f"{key}_lvl",
                           format_func=_label,
                           help=f"Your level: {profile['fitness_level']}." if profile.get("fitness_level") else None)
            st.toggle("Saved only", key=f"{key}_saved", help="Exercises you tapped Save on in the Exercise library.")
    create_form(username, key, exercises)
    mus, eq = set(st.session_state.get(f"{key}_mus") or []), set(st.session_state.get(f"{key}_eq") or [])
    cat, lvl = set(st.session_state.get(f"{key}_cat") or []), set(st.session_state.get(f"{key}_lvl") or [])
    saved = set(session_data.saved_workouts(username)) if st.session_state.get(f"{key}_saved") else None
    words = (q or "").strip().lower().split()
    found = [e for e in exercises
             if all(w in e["name"].lower() for w in words)
             and (not mus or mus & set(e.get("primaryMuscles") or []))
             and (not eq or _equip(e) in eq)
             and (not cat or e.get("category") in cat)
             and (not lvl or e.get("level") in lvl)
             and (saved is None or e["name"] in saved)]
    found = sorted(found, key=lambda e: e["name"].lower())
    if is_open:
        with panel, st.container(key=f"keep-{key}-fdone"):
            a, b = st.columns(2)
            a.button("Clear", key=f"{key}_clear", width="stretch", on_click=_clear, args=(key,), disabled=not active)
            b.button(f"Show {len(found)}", type="primary", key=f"{key}_fdone", help="Close filters and see the list",
                     width="stretch", on_click=_toggle, args=(key,))
    return found, (q or "").strip()


def _toggle(key):
    st.session_state[f"{key}_open"] = not st.session_state.get(f"{key}_open", False)


def _clear(key):
    for k in ("mus", "eq", "cat", "lvl", "saved"):
        st.session_state.pop(f"{key}_{k}", None)


def describe(e):
    """'Chest · Dumbbell': the main muscle and the equipment, for a list row ('Yours' first for your own)."""
    muscle = (e.get("primaryMuscles") or [""])[0]
    return "  ·  ".join(x for x in ("Yours" if e.get("custom") else "", _label(muscle) if muscle else "",
                                    _label(_equip(e))) if x)


# --- create your own exercise ----------------------------------------------------------------------------
def create_form(username, key, exercises):
    """'Create your own exercise': name, main muscle, equipment, reps or seconds, steps, and up to two photos
    (start, finish), which become the same labelled moving demo as every other exercise."""
    if not st.session_state.get(f"{key}_new"):
        st.button("Create your own exercise", icon=":material/add_circle:", key=f"{key}_newbtn", type="tertiary",
                  on_click=lambda: st.session_state.update({f"{key}_new": True, f"{key}_editing": None}))
        return
    editing = st.session_state.get(f"{key}_editing")
    muscles = _options([e for e in exercises if not e.get("custom")], "primaryMuscles")
    equip = _options([e for e in exercises if not e.get("custom")], "equipment")
    with st.form(f"{key}_newform", border=True):
        st.markdown(f"**Edit {editing}**" if editing else "**Create your own exercise**")
        st.text_input("Name", key=f"{key}_nname", max_chars=50, placeholder="e.g. Total Gym incline row")
        c1, c2 = st.columns(2)
        c1.selectbox("Main muscle", muscles, index=None, key=f"{key}_nmus", format_func=_label, placeholder="Pick one")
        c2.selectbox("Equipment", equip, index=equip.index("body only") if "body only" in equip else 0,
                     key=f"{key}_neq", format_func=_label)
        st.segmented_control("Counted in", ["Reps", "Seconds"], default="Reps", key=f"{key}_nkind")
        st.text_area("How to do it (one step per line)", key=f"{key}_nsteps", height=90,
                     placeholder="Sit facing the machine...\nPull the handles to your chest...\nLower slowly.")
        if editing:
            st.caption("Photos: upload new ones to replace them. If it has one photo now, adding one more makes it the "
                       "finish position, so the demo moves.")
        st.file_uploader("Photos: the start position, then the finish (optional)", type=["jpg", "jpeg", "png", "webp"],
                         accept_multiple_files=True, key=f"{key}_nphotos",
                         help="Two photos become a moving demo, like every other exercise. They're saved only "
                              "with your data, never on a public link.")
        a, b = st.columns(2)
        a.form_submit_button("Cancel", width="stretch",
                             on_click=lambda: st.session_state.update({f"{key}_new": False, f"{key}_editing": None}))
        b.form_submit_button("Save exercise", type="primary", width="stretch", on_click=_save_custom, args=(username, key))
    err = st.session_state.pop(f"{key}_nerr", None)
    if err:
        st.error(err)


def start_edit(key, ex):
    """Open the form filled in with one of your exercises (Exercise library > Yours)."""
    st.session_state.update({
        f"{key}_new": True, f"{key}_editing": ex["name"], f"{key}_nname": ex["name"],
        f"{key}_nmus": (ex.get("primaryMuscles") or [None])[0], f"{key}_neq": ex.get("equipment") or "body only",
        f"{key}_nkind": "Seconds" if ex.get("hold") else "Reps", f"{key}_nsteps": "\n".join(ex.get("instructions") or [])})


def _save_custom(username, key):
    from exercise_data import custom_list, find_exercise, make_custom, set_custom

    name = (st.session_state.get(f"{key}_nname") or "").strip()
    editing = st.session_state.get(f"{key}_editing")
    if not name:
        st.session_state[f"{key}_nerr"] = "Give your exercise a name."
        return
    if find_exercise(name) and not find_exercise(name).get("custom"):
        st.session_state[f"{key}_nerr"] = f"{name} is already in the library. Search for it instead."
        return
    new = list(st.session_state.get(f"{key}_nphotos") or [])
    old_photos = (find_exercise(editing) or {}).get("photos") or [] if editing else []
    photos = (old_photos + new if len(old_photos) == 1 and len(new) == 1  # one more photo: the finish position
              else new or old_photos)
    try:
        ex = make_custom(name, st.session_state.get(f"{key}_nmus"), st.session_state.get(f"{key}_neq"),
                         st.session_state.get(f"{key}_nkind") == "Seconds", st.session_state.get(f"{key}_nsteps") or "",
                         photos)
    except OSError:
        st.session_state[f"{key}_nerr"] = "One of the photos couldn't be read. Try a JPG or PNG."
        return
    items = [e for e in custom_list() if e["name"] not in (name, editing)] + [ex]
    session_data.save_settings(username, custom_exercises=items)
    set_custom(items)
    st.session_state.pop("_custom_media", None)  # rebuild its demo from the new photos
    st.session_state[f"{key}_new"] = False
    st.session_state[f"{key}_editing"] = None
    st.session_state[f"{key}_q"] = name  # show it straight away, ready to tap
    st.toast(f"{name} saved. Tap it to add it.", icon=":material/check_circle:")



# --- swap for a similar exercise (every editor uses this one) ----------------------------------------------
@st.dialog("Swap for a similar exercise")
def swap_dialog(name, hold, avoid, on_pick):
    """Three exercises for the same main muscles (training.alternatives). Picking one calls on_pick(new_name)."""
    import training
    import ui
    from exercise_data import find_exercise, load_exercises, prepare_minis

    alts = training.alternatives(name, load_exercises(), 3, avoid=set(avoid), hold=hold)
    st.markdown(f"Instead of **{name}**:")
    if not alts:
        st.caption("No close match in the library for this one. You can remove it and add any exercise instead.")
    minis = prepare_minis([e for e in (find_exercise(a) for a in alts) if e])
    for n, alt in enumerate(alts):
        opened, acted = ui.tap_row(f"swap{n}", minis.get(alt), alt, describe(find_exercise(alt) or {}), action="Swap")
        if opened or acted:
            on_pick(alt)
            st.rerun()
    if st.button("Keep it", key="swap_keep", width="stretch", type="tertiary"):
        st.rerun()
