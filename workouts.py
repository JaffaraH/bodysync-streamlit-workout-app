import streamlit as st

import session_data
import ui
from exercise_data import (
    exercise_gif, find_exercise, has_demo, load_exercises, prepare_demos, prepare_thumbs, update_database,
)

PAGE_SIZE = 6  # cards per page: short enough to scan on a phone (the database has ~870 exercises)
SECTIONS = ["Explore", "Saved", "Yours"]


def workouts_page(username, pages):
    ui.back_to_you(pages)
    st.title("Exercise library")
    st.caption("Save keeps an exercise here under Saved (and in Filters > Saved only when you build a playlist). "
               "Add to playlist puts it in one of your playlists in Library.")
    section = st.segmented_control("Section", SECTIONS, default=SECTIONS[0], key="wk_section", label_visibility="collapsed")
    if (section or SECTIONS[0]) == "Saved":
        saved_workouts_view(username, pages)
    elif section == "Yours":
        yours_view(username)
    else:
        explore_workouts(username, pages)
    st.page_link(pages["lifts"], label="Your playlists are in Library", icon=":material/bookmarks:")


def _go(section):
    st.session_state["wk_section"] = section


# --- one exercise card, shared by Explore and Saved --------------------------
@st.fragment
def _save_button(username, exercise, prefix):
    """Reruns only this button, so saving never re-renders the whole page."""
    name, ex_id = exercise["name"], exercise["id"]
    undo_key = f"undo_{ex_id}"
    if name in session_data.saved_workouts(username):
        if st.button("Saved", icon=":material/check:", key=f"{prefix}_rm_{ex_id}", help="Click to remove from saved"):
            with st.spinner("Removing..."):
                session_data.unsave_workout(username, name)
            st.session_state[undo_key] = True
            st.rerun(scope="fragment")
    elif st.session_state.get(undo_key):
        c1, c2 = st.columns([2, 1], vertical_alignment="center")
        c1.caption("Removed from saved.")
        if c2.button("Undo", key=f"{prefix}_undo_{ex_id}"):
            session_data.save_workout(username, name)
            st.session_state.pop(undo_key, None)
            st.rerun(scope="fragment")
    elif st.button("Save", key=f"{prefix}_save_{ex_id}", type="primary", icon=":material/bookmark_add:"):
        try:
            with st.spinner("Saving..."):
                session_data.save_workout(username, name)
            st.toast(f"{name} saved", icon=":material/check_circle:")
            st.rerun(scope="fragment")
        except Exception as e:
            st.error(f"Couldn't save ({type(e).__name__}). Try again.")


def exercise_card(username, exercise, prefix, pages=None):
    with st.container(border=True):
        img_col, info_col = st.columns([1, 1.3])
        with img_col:
            gif = exercise_gif(exercise)
            if gif:
                ui.demo(gif)
            else:
                st.caption("No demo image for this exercise yet.")
        with info_col:
            st.subheader(exercise["name"], anchor=False)
            ui.badges(exercise.get("level"), exercise.get("equipment"), exercise.get("category"))
            primary = ", ".join(exercise.get("primaryMuscles") or [])
            secondary = ", ".join(exercise.get("secondaryMuscles") or [])
            if primary:
                st.caption(f"**Targets:** {primary}" + (f"  \n**Also works:** {secondary}" if secondary else ""))
            with st.expander("How to do it"):
                for i, step in enumerate(exercise.get("instructions") or [], 1):
                    st.markdown(f"{i}. {step}")
            _save_button(username, exercise, prefix)
            if pages:
                _add_to_playlist(username, exercise, prefix, pages)


def _add_to_playlist(username, exercise, prefix, pages):
    """Put this exercise in a playlist you have (it lands at the end, 3 sets), or start a new one with it."""
    import playlist_builder
    import training

    name = exercise["name"]
    with st.popover("Add to playlist", icon=":material/playlist_add:"):
        mine = session_data.routines(username)
        if mine:
            pick = st.selectbox("Your playlists", mine, key=f"{prefix}_pl_{exercise['id']}")
            have = {i["workout_name"] for i in session_data.routine_items(username, pick)}
            if name in have:
                st.caption(f"Already in {pick}.")
            elif st.button(f"Add to {pick}", type="primary", key=f"{prefix}_pladd_{exercise['id']}", width="stretch"):
                hold = training.kind_of(name) == "hold"
                session_data.add_routine(username, pick, [name], 3, 30 if hold else 10, 0)
                st.toast(f"Added {name} to {pick}", icon=":material/check_circle:")
        if st.button("New playlist with this", icon=":material/add:", key=f"{prefix}_plnew_{exercise['id']}",
                     width="stretch"):
            playlist_builder.start(username, picked=[name])
            st.switch_page(pages["lifts"])


# --- Explore ------------------------------------------------------------------
def explore_workouts(username, pages=None):
    import exercise_picker

    filtered, q = exercise_picker.search(username, load_exercises(), "ex", only_with_demo=False)
    sig_extra = tuple(tuple(st.session_state.get(f"ex_{k}") or ()) for k in ("mus", "eq", "cat", "lvl")) + (
        bool(st.session_state.get("ex_saved")),)

    left, right = st.columns([3, 1], vertical_alignment="center")
    left.caption(f"{len(filtered)} exercise{'s' if len(filtered) != 1 else ''}"
                )
    if right.button("Check for new exercises", icon=":material/sync:", width="stretch", help="Looks for exercises added to the open Free Exercise DB."):
        with st.spinner("Checking for updates..."):
            result = update_database()
        if result["status"] == "offline":
            st.toast("Couldn't reach the exercise database. Are you online?", icon=":material/warning:")
        elif result["added"]:
            st.toast(f"{len(result['added'])} new exercise(s): {', '.join(result['added'][:3])}", icon="🆕")
            st.rerun()
        else:
            st.toast("You're up to date.", icon=":material/check_circle:")

    if not filtered:
        ui.empty_state("No exercises match", "Try a shorter search or remove a filter.", icon="search")
        return

    # page state resets whenever the filters change
    sig = (q,) + sig_extra
    if st.session_state.get("ex_sig") != sig:
        st.session_state.update(ex_sig=sig, ex_page=1)
    pages_total = max(1, -(-len(filtered) // PAGE_SIZE))
    page = min(st.session_state.get("ex_page", 1), pages_total)
    items = filtered[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

    missing = [e for e in items if not has_demo(e) and e.get("images")]
    if missing:  # first view of these exercises: show honest progress, not a frozen page
        with st.status(f"Preparing {len(missing)} demo animation(s) (first view only)...", expanded=True) as status:
            bar = st.progress(0.0)
            prepare_demos(items, on_progress=lambda i, n: bar.progress(i / n))
            status.update(label="Demos ready", state="complete", expanded=False)

    for e in items:
        exercise_card(username, e, "ex", pages)

    prev_col, mid, next_col = st.columns([1, 2, 1], vertical_alignment="center")
    if prev_col.button("Previous", icon=":material/arrow_back:", disabled=page <= 1, width="stretch"):
        st.session_state["ex_page"] = page - 1
        st.rerun()
    mid.markdown(f"<p style='text-align:center'>Page {page} of {pages_total}</p>", unsafe_allow_html=True)
    if next_col.button("Next", icon=":material/arrow_forward:", icon_position="right", disabled=page >= pages_total, width="stretch"):
        st.session_state["ex_page"] = page + 1
        st.rerun()


# --- Saved --------------------------------------------------------------------
def saved_workouts_view(username, pages=None):
    names = sorted(session_data.saved_workouts(username))
    if not names:
        ui.empty_state("Nothing saved yet", "Tap Save on any exercise and it will show up here.", icon="bookmark")
        st.button("Browse exercises", on_click=_go, args=("Explore",), type="primary")
        return
    st.caption(f"{len(names)} saved")
    for name in names:
        exercise = find_exercise(name)
        if exercise:
            exercise_card(username, exercise, "sv", pages)
        else:
            st.warning(f"'{name}' is no longer in the exercise database.")



# --- your own exercises -------------------------------------------------------------------------
def yours_view(username):
    """Exercises you made (also creatable from any exercise picker). They show up everywhere you pick exercises."""
    import exercise_picker
    from exercise_data import custom_list, mini_url, set_custom

    exercise_picker.create_form(username, "yc", load_exercises())
    mine = custom_list()
    if mine:
        st.caption("Tap one to edit it. They show up in every exercise picker, marked Yours.")
    if not mine:
        st.caption("Nothing here yet. Machines at your gym, equipment at home, or a move you like that the library "
                   "doesn't have: create it once and use it in any playlist or workout.")
        return
    for n, e in enumerate(mine):
        photos = len(e.get("photos") or [])
        detail = exercise_picker.describe(e) + ("  ·  moving demo" if photos == 2 else "  ·  1 photo" if photos else
                                                "  ·  no photo")
        opened, acted = ui.tap_row(f"yc{n}", mini_url(e) or "fitness_center", e["name"], detail,
                                   icon=not photos, action="Remove")
        if acted:
            items = [x for x in mine if x["name"] != e["name"]]
            session_data.save_settings(username, custom_exercises=items)
            set_custom(items)
            st.toast(f"{e['name']} removed. Workouts you already logged keep it.", icon=":material/check_circle:")
            st.rerun()
        if opened:  # tap to edit: same form, filled in
            exercise_picker.start_edit("yc", e)
            st.rerun()
