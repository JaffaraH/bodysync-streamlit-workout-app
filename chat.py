"""FitBuddy AI: two tools that turn one AI answer into something you use in the app, not just read.

* Build my plan: goal, days, minutes, the equipment you have (from the exercise library's own list), what to focus on,
  and anything else in your own words -> Gemini picks exercises ONLY from the library -> one card per day. Each day can
  be edited in the playlist editor (so nobody spends AI requests on small changes) or saved as it is, and the saved
  days can go straight onto your week.
* Gym machine photo: Gemini says what the machine is and how to use it (or that it isn't gym equipment) -> save it
  as one of your own exercises.
Answers come back as JSON (ai.ask_json) and are checked against the library before anything is saved.
"""
import streamlit as st
from PIL import Image, UnidentifiedImageError

import ai
import session_data
import ui
from exercise_data import find_exercise, load_exercises, prepare_minis

GOALS = ["Build muscle", "Get stronger", "Lose weight", "Build stamina", "Move better"]
FOCUS = ["Chest", "Back", "Shoulders", "Arms", "Glutes", "Legs", "Abs and core"]
TOOLS = ["Build my plan", "Gym machine photo"]
CSS = """<style>
.st-key-fb-tools [data-testid="stElementContainer"], .st-key-fb-tools [data-testid="stButtonGroup"],
.st-key-fb-tools [data-testid="stButtonGroup"] > div { width: 100% !important; max-width: none !important; }
.st-key-fb-tools [data-testid="stButtonGroup"] button { flex: 1 1 0 !important; min-width: 0; }
</style>"""


def chat_page(username, pages):
    ui.back_to_you(pages)
    st.title("FitBuddy AI")
    st.caption("Ask for a plan built from the exercise library, or snap a gym machine to learn it and save it.")
    ui.ai_key_notice(username)
    st.html(CSS)
    with st.container(key="fb-tools"):
        tool = st.segmented_control("Tool", TOOLS, default=TOOLS[0], key="fb_tool", label_visibility="collapsed")
    if (tool or TOOLS[0]) == TOOLS[0]:
        plan_tool(username, pages)
    else:
        machine_tool(username)
    st.caption("General guidance from an AI, not medical advice. On Gemini's free tier, Google may use what you send "
               "to improve its products, so don't include anything private.")


def _no_ai_note():
    if not ai.is_configured():
        st.caption(":material/key: Turn on AI above to use this.")


# --- 1. a plan you can edit, save and schedule -----------------------------------------------------------
def _equipment_options():
    import exercise_picker

    return exercise_picker._options([e for e in load_exercises() if e.get("images")], "equipment")


def _library_for(equipment):
    """Exercise names the AI may choose from: with a demo, and only for the equipment you have."""
    allowed = set(equipment) | {"body only"}
    return sorted(e["name"] for e in load_exercises()
                  if e.get("images") and (e.get("equipment") or "body only") in allowed
                  and e.get("category") in ("strength", "stretching", "plyometrics", "cardio"))


def plan_tool(username, pages):
    import exercise_picker

    with st.form("plan_form", border=False):
        goal = st.pills("Your goal", GOALS, default=GOALS[0], key="fb_goal")
        c1, c2 = st.columns(2)
        days = c1.slider("Days a week", 1, 6, 3)
        minutes = c2.select_slider("Minutes each", [20, 30, 45, 60, 75, 90], value=45)
        gear = st.pills("Equipment you have", _equipment_options(), selection_mode="multi", default=["body only"],
                        key="fb_gear", format_func=exercise_picker._label)
        focus = st.pills("Focus on (optional)", FOCUS, selection_mode="multi", key="fb_focus")
        w1, w2 = st.columns(2)
        steps = w1.select_slider("Walking: steps a day", ["Off", "5,000", "6,000", "7,000", "8,000", "10,000", "12,000"],
                                 value="Off", key="fb_steps")
        walk_days = w2.slider("Walking days a week", 1, 7, 5, key="fb_walk_days")
        st.caption("Not sure? Studies saw most of the benefit at about 8,000 to 10,000 steps a day, or 6,000 to 8,000 "
                   "if you're 60 or over. Any amount more than you do now counts.")
        walk = (steps, walk_days) if steps != "Off" else None
        extra = st.text_area("Anything else, in your own words (optional)", key="fb_extra", height=80,
                             placeholder="e.g. I want to get my first push-up. A squat day each week. "
                                         "My left knee hurts on lunges.")
        go = st.form_submit_button("Build my plan", type="primary", icon=":material/auto_awesome:",
                                   disabled=not ai.is_configured(), width="stretch")
    _no_ai_note()
    if go:
        names = _library_for(gear or ["body only"])
        prompt = f"""You are a certified strength coach. Build a {days}-day weekly plan.
Goal: {goal or 'general fitness'}. About {minutes} minutes per session (count about 2 minutes per set with rest).
Focus a bit more on: {', '.join(focus) or 'a balanced mix'}.
Walking habit: {f'{walk[0]} steps a day on {walk[1]} days a week; mention it in the tips' if walk else 'none'}.
In their own words: {extra.strip() or 'nothing else'}
About them: {session_data.profile_summary(username)}
Use ONLY exercise names from this list, spelled exactly as written: {"; ".join(names)}
Balance muscles across the week, put big lifts first, and keep each day within the time.
Reply as JSON only: {{"days": [{{"name": "short day name", "exercises": [{{"name": "...", "sets": 3,
"reps": 10, "seconds": false}}]}}], "tips": ["one short tip", "another"]}}. Use "seconds": true for timed holds."""
        with st.spinner("Building your plan from the exercise library..."):
            try:
                st.session_state["fb_plan"] = ai.ask_json(prompt, username=username)
                st.session_state["fb_plan_walk"] = walk
                for k in [k for k in st.session_state if k.startswith("fb_saved_")]:
                    del st.session_state[k]  # a new plan: nothing saved yet
            except Exception as e:
                st.error(ai.friendly_error(e))
                return
    plan = st.session_state.get("fb_plan")
    if plan:
        _show_plan(username, pages, plan)


def clean_day(day):
    """Keep only exercises that really are in the library, with numbers in sensible ranges.
    Returns ([(name, sets, reps_or_seconds, is_seconds)], how many were left out)."""
    out, skipped = [], 0
    for x in day.get("exercises") or []:
        ex = find_exercise(str(x.get("name", "")))
        if not ex:
            skipped += 1
            continue
        try:
            sets, reps = int(x.get("sets") or 3), int(x.get("reps") or 10)
        except (TypeError, ValueError):
            sets, reps = 3, 10
        sec = bool(x.get("seconds"))
        out.append((ex["name"], min(8, max(1, sets)), min(600 if sec else 50, max(1, reps)), sec))
    return out, skipped


def _save_day(username, title, moves):
    import playlist_builder

    name = playlist_builder._free_name(username, str(title)[:40])
    for n, sets, reps, _ in moves:
        session_data.add_routine(username, name, [n], sets, reps, 0)
    return name


def _edit_day(username, pages, i, title, moves):
    """Open this day in the playlist editor (rename, reorder, swap, sets and reps); saving comes back here."""
    import playlist_builder

    playlist_builder.start(username, picked=[n for n, *_ in moves], name=str(title)[:40],
                           amounts={n: [s, r] for n, s, r, _ in moves}, back_to=("fitbuddy", f"fb_saved_{i}"))
    st.switch_page(pages["lifts"])


def _show_plan(username, pages, plan):
    st.markdown("##### Your plan")
    st.caption("Edit any day before saving: same editor as your playlists, no AI needed. Or save it as it is.")
    days = [(d.get("name") or f"Day {i + 1}", *clean_day(d)) for i, d in enumerate(plan.get("days") or [])]
    days = [d for d in days if d[1]]
    if not days:
        st.warning("The AI's plan didn't match the exercise library. Try again, or pick more equipment.")
        return
    for i, (title, moves, skipped) in enumerate(days):
        saved = st.session_state.get(f"fb_saved_{i}")
        with st.container(border=True):
            st.markdown(f"**{ui.no_media(title)}**" + (f"  ·  :green[saved as {saved}]" if saved else ""))
            minis = prepare_minis([find_exercise(n) for n, *_ in moves])
            ui.tracklist([(minis.get(n), n, f"{s} × {r} s" if sec else f"{s} × {r} reps") for n, s, r, sec in moves])
            if skipped:
                st.caption(f"{skipped} suggestion{'s' if skipped != 1 else ''} weren't in the library and were left out.")
            if not saved:
                with st.container(key=f"keep-fb-day-{i}"):
                    a, b = st.columns(2)
                    if a.button("Edit", icon=":material/edit:", key=f"fb_edit_{i}", width="stretch"):
                        _edit_day(username, pages, i, title, moves)
                    if b.button("Save as is", icon=":material/bookmark_add:", key=f"fb_save_{i}", width="stretch"):
                        st.session_state[f"fb_saved_{i}"] = _save_day(username, title, moves)
                        st.rerun()
    for tip in (plan.get("tips") or [])[:3]:
        st.caption(ui.no_media(f"Tip: {tip}"))
    left = [i for i in range(len(days)) if not st.session_state.get(f"fb_saved_{i}")]
    saved_names = [st.session_state[f"fb_saved_{i}"] for i in range(len(days)) if st.session_state.get(f"fb_saved_{i}")]
    from home import HOME_CSS  # the same big centred button as Home
    st.html(HOME_CSS)
    with st.container(key="bs-homestart"):
        if left:
            if st.button(f"Save {'all days' if len(left) == len(days) else 'the rest'} as playlists", type="primary",
                         icon=":material/library_add:", key="fb_save_all", width="stretch"):
                for i in left:  # only the days not saved yet: no duplicates
                    st.session_state[f"fb_saved_{i}"] = _save_day(username, days[i][0], days[i][1])
                st.rerun()
        elif st.button("Put these days on my week", type="primary", icon=":material/calendar_month:",
                       key="fb_week", width="stretch"):
            st.session_state["fb_week_days"] = _put_on_week(username, saved_names)
            st.rerun()
    put = st.session_state.pop("fb_week_days", None)
    if put:
        st.success("On your week: " + ", ".join(put) + ". Change any day in Plan my week.", icon=":material/check_circle:")
        st.page_link(pages["home"], label="See it on Home", icon=":material/home:")
    elif not left:
        st.caption("All days are saved as playlists in Library. Put them on your week, or open them to start.")


def _put_on_week(username, names):
    """Spread the saved days across the week (a day off between where possible); walks on the other days if asked."""
    import plan

    days = plan.SPREAD.get(len(names), list(range(len(names))))
    week = dict(plan.get(username))
    for d, name in zip(days, names):
        week[str(d)] = f"rt:{name}"
    plan.save(username, week)
    walk = st.session_state.get("fb_plan_walk")
    if walk:  # the same walking habit as Plan my week: rest days first, then workout days
        steps, n = int(walk[0].replace(",", "")), walk[1]
        order = [d for d in range(7) if str(d) not in week] + [d for d in range(7) if str(d) in week]
        session_data.save_settings(username, walk_habit={"steps": steps, "days": sorted(order[:n])})
    return [f"{plan.DAYS[d][:3]} {n}" for d, n in zip(days, names)]


# --- 2. a gym machine you can save -----------------------------------------------------------------------
def machine_tool(username):
    st.caption("Upload a photo of a gym machine (or equipment at home). You'll get how to use it, and you can save "
               "it as one of your own exercises.")
    file = st.file_uploader("Photo of the machine", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed")
    if file is None:
        _no_ai_note()
        return
    try:
        img = Image.open(file)
    except (UnidentifiedImageError, OSError):
        st.error("That file couldn't be read as an image. Try a JPG or PNG.")
        return
    st.image(img, width=320)
    key = f"fb_machine_{file.file_id}"
    if st.button("Explain this machine", type="primary", icon=":material/auto_awesome:", key="fb_explain",
                 disabled=not ai.is_configured(), width="stretch"):
        muscles = sorted({m for e in load_exercises() for m in (e.get("primaryMuscles") or [])})
        prompt = (
            "Look at this photo. First decide if it shows gym or exercise equipment. If it doesn't, or you can't tell, "
            "reply {\"is_equipment\": false} and nothing else; never guess. Otherwise reply as JSON only: "
            "{\"is_equipment\": true, \"name\": \"common name\", \"muscle\": one of "
            f"{muscles}, \"setup\": \"seat, pad or weight setup in one sentence\", \"steps\": [\"3 to 5 short steps\"], "
            "\"mistake\": \"one common mistake to avoid\", \"seconds\": false}")
        with st.spinner("Looking at your photo..."):
            try:
                st.session_state[key] = ai.ask_json(prompt, image=img, username=username)
            except Exception as e:
                st.error(ai.friendly_error(e))
                return
    _no_ai_note()
    info = st.session_state.get(key)
    if not info:
        return
    if not info.get("is_equipment") or not info.get("steps"):
        st.info("This doesn't look like gym equipment, or the photo isn't clear enough to tell. Try a photo of the "
                "whole machine, from the side.", icon=":material/help:")
        return
    st.markdown(f"#### {ui.no_media(info.get('name'))}")
    if info.get("muscle"):
        st.caption(f"Works: {info['muscle']}")
    if info.get("setup"):
        st.markdown(ui.no_media(f"**Set up:** {info['setup']}"))
    for i, step in enumerate(info.get("steps") or [], 1):
        st.markdown(ui.no_media(f"{i}. {step}"))
    if info.get("mistake"):
        st.caption(ui.no_media(f"**Watch out:** {info['mistake']}"))
    if st.button("Save as my exercise", icon=":material/add_circle:", key="fb_machine_save", width="stretch"):
        from exercise_data import custom_list, make_custom, set_custom

        file.seek(0)
        ex = make_custom(str(info.get("name") or "My machine")[:50], info.get("muscle"), "machine",
                         bool(info.get("seconds")), "\n".join(info.get("steps") or []), [file])
        items = [e for e in custom_list() if e["name"] != ex["name"]] + [ex]
        session_data.save_settings(username, custom_exercises=items)
        set_custom(items)
        st.success(f"Saved {ex['name']}. It's in every exercise picker, marked Yours. To change it or add a finish "
                   "photo for a moving demo, open Exercise library > Yours.", icon=":material/check_circle:")
