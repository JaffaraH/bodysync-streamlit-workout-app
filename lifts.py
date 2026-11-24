"""Library: everything that's yours. Pills: This week (your plan), Playlists (saved workouts), Lifts (the
exercises you track, and workouts built from them), History (what you did).

Lifts: the exercises you train, with your best set on each.

A list of rows (photo, name, best set, last done). Open one to see big numbers (best, last, next),
edit it in place, or remove it. Everything is visible: no expanders, no popovers.
"""
import streamlit as st

import session_data
import training
import playlist_builder
import ui
from exercise_data import exercise_gif, find_exercise, load_exercises, mini_url, prepare_minis, anim_url, thumb_url

DAYS = ["upper", "lower", "core"]
FILTERS = ["All", "Upper", "Lower", "Core"]
DRAFT_KEYS = ("new_pr_w", "new_pr_r", "lifts_pick", "lifts_filter")


def _history(sets, name):
    return [s for s in sets if s["exercise"] == name]


def lifts_page(username, pages):
    if st.session_state.pop("_pb_goto_plan", False):  # a planned day was edited here: back to the planner
        st.session_state["t_go"] = True
        st.switch_page(pages["workout"])
    back = st.session_state.pop("_pb_goto", None)  # opened from another page (FitBuddy): go back there
    if back in pages:
        st.switch_page(pages[back])
    ui.keep(*DRAFT_KEYS)
    unit = session_data.unit(username)
    lifts = session_data.lifts(username)
    have = {l["exercise"] for l in lifts}
    open_name = st.session_state.get("lift_open")
    if open_name and open_name in have:
        _detail(username, next(l for l in lifts if l["exercise"] == open_name), unit)
        return

    view = st.session_state.get("lib_view")
    if view and view[0] == "pl" and view[1] in session_data.routines(username):
        _playlist_page(username, pages, view[1])
        return
    if view and view[0] == "build":
        playlist_builder.page(username, pages)
        return

    st.title("Library")
    st.html(ROW_CSS)
    tabs = ["This week", "Playlists", "Lifts", "History"]
    want = st.session_state.pop("lib_tab_next", None)
    if want in tabs:
        st.session_state["lib_tab"] = want
    if st.session_state.get("lib_tab") not in tabs:
        st.session_state["lib_tab"] = tabs[0]
    tab = st.segmented_control("Show", tabs, key="lib_tab", label_visibility="collapsed") or tabs[0]
    st.write("")
    if tab == "This week":
        _this_week(username, pages)
    elif tab == "Playlists":
        _routines(username, pages)
    elif tab == "History":
        _recent(username, pages, limit=15)
    else:
        _lifts_tab(username, pages, lifts, unit)
    ui.remember(*DRAFT_KEYS)


def _lifts_tab(username, pages, lifts, unit):
    """The lifts you track: your best set on each (used to pick starting weights and spot records)."""
    if len(lifts) >= 3:
        import today

        st.subheader("Train from your lifts", anchor=False)
        today.from_lifts(username, pages)
        st.write("")
    head, add = st.columns([3, 2], vertical_alignment="center")
    head.subheader("Your lifts", anchor=False)
    if add.button("Add a lift", icon=":material/add:", key="lift_add_open", width="stretch"):
        st.session_state["lift_adding"] = not st.session_state.get("lift_adding")
    if st.session_state.get("lift_adding"):
        _add_form(username, unit)
        st.divider()
    if not lifts:
        st.caption("Lifts you log in a workout appear here with your best set. Or add one now.")
        return
    st.caption("Every exercise you have logged in any workout or playlist, with your best set. It sets your starting "
               "weight next time. Tap one to see it, change it, or remove it.")
    unit_pick = st.segmented_control("Weight unit", ["lb", "kg"], default=unit, key="unit_ctl")
    if unit_pick and unit_pick != unit:
        session_data.set_unit(username, unit_pick)
        st.rerun()
    sets = session_data.all_sets(username)
    thumbs = prepare_minis([e for e in (find_exercise(l["exercise"]) for l in lifts) if e])
    for n, lift in enumerate(lifts):
        name = lift["exercise"]
        hist = _history(sets, name)
        best = training.amount(lift["pr_weight"], lift["pr_reps"], unit) if lift.get("pr_weight") else "No best set yet"
        last = f"last {_ago(training.days_since(hist[-1]['performed_at']))}" if hist else "not done yet"
        opened, _ = ui.tap_row(f"lift{n}", thumbs.get(name), name, f"Best {best}  ·  {last}")
        if opened:
            _open(name)
            st.rerun()


def _start(username, pages, names, template, source, day="custom", from_page="lifts"):
    import today

    st.session_state.update(t_template=template, t_day=day, t_source=source, t_from_page=from_page)
    today._begin(username, names)
    ui.to_workout(pages)


def _skill_pic(username, name):
    """A skill block's picture: the skill's own cover (its goal step's demo, or your photo)."""
    if not name.startswith("Skill: "):
        return None
    import skills as skills_page
    import skills_logic as sk_
    lad = sk_.all_ladders(session_data.custom_skills(username)).get(name[7:])
    return skills_page._cover_url(lad) if lad else None


def _label_item(username, name):
    """A playlist item as people read it: exercise names as they are, a skill block as 'Front splits practice'."""
    if name.startswith("Skill: "):
        import skills_logic as sk_
        lad = sk_.all_ladders(session_data.custom_skills(username)).get(name[7:])
        return f"{lad['title']} practice" if lad else "Skill practice"
    return name


def _playlist_parts(username, name):
    items = session_data.routine_items(username, name)
    names = list(dict.fromkeys(i["workout_name"] for i in items))
    by = {i["workout_name"]: i for i in items}
    return names, by


def _playlist_meta(username, name):
    import today

    names, by = _playlist_parts(username, name)
    lifts_ = [(n, int(by[n]["sets"] or 3)) for n in names if not n.startswith("Skill: ")]
    mins = today._minutes(lifts_) + 5 * sum(1 for n in names if n.startswith("Skill: ")) if names else 0
    first = next((find_exercise(n) for n in names if find_exercise(n)), None)
    return names, by, mins, (mini_url(first) if first else None)


def _routines(username, pages):
    """Your playlists: picture, name, how many moves and minutes. Tap one to see it, start it or change it."""
    if st.button("New playlist", icon=":material/add:", key="pl_new", type="primary"):
        playlist_builder.start(username)
        st.rerun()
    names = session_data.routines(username)
    if not names:
        st.caption("Make your own, or save any workout from Workouts (or after you finish one).")
        return
    for n, name in enumerate(names):
        parts, _, mins, pic = _playlist_meta(username, name)
        opened, _ = ui.tap_row(f"pl{n}", pic, name, f"{len(parts)} move{'s' if len(parts) != 1 else ''}  ·  about {mins} min")
        if opened:
            st.session_state["lib_view"] = ("pl", name)
            st.rerun()


def _playlist_template(username, name):
    names, by = _playlist_parts(username, name)
    return names, {n: {"sets": int(by[n]["sets"] or 3), "rep_low": int(by[n]["reps"] or 8),
                       "rep_high": int(by[n]["reps"] or 8) + 4} for n in names if not n.startswith("Skill: ")}


def _playlist_page(username, pages, name):
    """One playlist, like a workout preview: what's in it, then Start. Edit and Remove are here too."""
    import today

    if st.button("Playlists", icon=":material/arrow_back:", key="pl_back"):
        st.session_state.pop("lib_view", None)
        st.session_state["lib_tab_next"] = "Playlists"
        st.rerun()
    names, by, mins, pic = _playlist_meta(username, name)
    first = next((find_exercise(n) for n in names if find_exercise(n)), None)
    ui.hero("Your playlist", name, f"{len(names)} moves  ·  about {mins} min", anim_url(first, labels=False) if first else None)
    minis = prepare_minis([e for e in (find_exercise(n) for n in names) if e])
    made = st.session_state.pop("pl_made", None)
    if made and made[1] == name:
        _made_dialog(username, pages, made)
    ui.tracklist([(minis.get(n) or _skill_pic(username, n), _label_item(username, n),
                   "Drills, then your current step" if n.startswith("Skill: ")
                   else f"{int(by[n]['sets'] or 3)} sets · {int(by[n]['reps'] or 8)}" + (" s" if training.kind_of(n) == "hold" else " reps"))
                  for n in names])
    with st.container(key="keep-pl-actions"):
        a, b = st.columns(2)
        if a.button("Edit", icon=":material/edit:", key="pl_edit", width="stretch"):
            playlist_builder.start(username, editing=name)
            st.rerun()
        if b.button("Remove", icon=":material/delete:", key="pl_rm", width="stretch"):
            _remove_playlist_dialog(username, name)
    st.html(today.SESSION_CSS)
    with st.container(key="bs-donebar"):
        if st.button("Start", type="primary", icon=":material/play_arrow:", key="pl_go", width="stretch"):
            parts, template = _playlist_template(username, name)
            st.session_state.pop("lib_view", None)
            _start(username, pages, parts, template, name)


@st.dialog(" ")
def _made_dialog(username, pages, made):
    """The moment a playlist is made: its pictures stack in, a tick, then one clear next step."""
    kicker, name, pics = made
    ui.created(kicker, name, pics)
    st.caption("It's in Library > Playlists. You can put it on any day in Plan my week.")
    if st.button("Start it now", type="primary", icon=":material/play_arrow:", key="made_go", width="stretch"):
        parts, template = _playlist_template(username, name)
        st.session_state.pop("lib_view", None)
        _start(username, pages, parts, template, name)
    if st.button("Done", key="made_done", width="stretch"):
        st.rerun()


@st.dialog("Remove this playlist?")
def _remove_playlist_dialog(username, name):
    st.write(f"{name} will be removed. Workouts you already did with it stay in your history.")
    if st.button("Remove", type="primary", width="stretch", key="pl_rm_ok"):
        session_data.delete_routine(username, name)
        st.session_state.pop("lib_view", None)
        st.toast(f"{name} removed", icon=":material/check_circle:")
        st.rerun()
    if st.button("Keep it", width="stretch", key="pl_rm_no"):
        st.rerun()


def _open_planned(username, pages, key):
    """Tap a day: see that workout first (preview), not a surprise start."""
    import plan as wp

    kind, _, ref = key.partition(":")
    if kind == "cur":
        st.session_state.update(t_phase="template", t_tpl=ref, t_tpl_from="home")
        ui.to_workout(pages)
    elif kind == "rt":
        st.session_state["lib_view"] = ("pl", ref)
        st.rerun()
    elif kind == "sk":
        st.session_state["sk_view"] = ("skill", ref)
        st.switch_page(pages["skills"])
    else:
        wp.start(username, pages, key)


def _week_rows(username, pages, plan, live=True):
    """Each planned day as a picture row. Today: Start. Another day: Do today (swaps it with today)."""
    import plan as wp
    from datetime import date

    today_i = date.today().weekday()
    sets = session_data.all_sets(username)
    dots = training.week_dots([x for x in sets if not x["exercise"].startswith("Walk:")])  # workouts done
    walked = training.week_dots([x for x in sets if x["exercise"].startswith("Walk:")])  # walks done
    for d in range(7):
        key = plan.get(str(d))
        if not key:
            steps = wp.walk_today(username, d)
            if steps:  # a walk-only day: shown so the week is complete, ticked off on Home
                state = "done" if live and walked[d] else "now" if d == today_i else ""
                ui.tap_row(f"wkw{d}", "directions_walk", f"Walk {steps:,} steps", "Walking habit",
                           kicker=wp.DAYS[d] + (" · done" if state == "done" else " · today" if state == "now" else ""),
                           kicker_state=state, icon=True, end=" ")
            continue
        info = wp.describe(username, key)
        title = info[0] if info else wp.label(username, key)
        extra = wp.day_skill(username, d)
        if extra:
            title += f" + {wp.label(username, extra).replace('Practise: ', '')}"
        steps = wp.walk_today(username, d)
        if steps:
            title += f" + {steps // 1000}k walk"
        meta = info[2].split("  ·  ")[-1] if info else ""
        pic = info[1] if info else None
        state = "done" if live and dots[d] else "now" if d == today_i else ""
        kicker = wp.DAYS[d] + (" · done" if state == "done" else " · today" if state == "now" else "")
        action = None
        if live and not dots[d]:
            action = "Start" if d == today_i else "Do today"
        opened, acted = ui.tap_row(f"wk{d}", pic, title, meta, kicker=kicker, kicker_state=state, action=action)
        if acted and d == today_i:
            wp.start(username, pages, key, d)
        elif acted:  # move that workout to today; today's (if any) takes its place
            new = dict(plan)
            new[str(d)], new[str(today_i)] = plan.get(str(today_i), wp.REST), key
            wp.save(username, new)
            st.toast(f"{title} moved to today", icon=":material/swap_vert:")
            st.rerun()
        elif opened:
            _open_planned(username, pages, key)


def _this_week(username, pages):
    """Your plan for the week, or a suggested one from your goal (one tap to use it, or change it)."""
    import plan as wp

    plan = wp.get(username)
    if plan:
        _week_rows(username, pages, plan)
        st.write("")
        if st.button("Edit my week", icon=":material/edit_calendar:", key="lib_plan_edit"):
            for k in [k for k in st.session_state if k.startswith("wp_")]:
                del st.session_state[k]
            st.session_state.update(t_phase="plan", wp_step=3)
            ui.to_workout(pages)
        return
    goal = wp.default_goal(username)
    draft = wp.suggest(username, None, goal)
    st.caption(f"No plan yet. A suggested week for your goal ({wp.GOALS[goal][0].lower()}):")
    _week_rows(username, pages, draft, live=False)
    st.write("")
    a, b = st.columns(2)
    if a.button("Use this week", type="primary", icon=":material/check:", key="lib_plan_use", width="stretch"):
        wp.save(username, draft)
        session_data.save_settings(username, plan_goal=goal)
        st.toast("Your week is planned. Home shows today's.", icon=":material/check_circle:")
        st.rerun()
    if b.button("Change it", icon=":material/tune:", key="lib_plan_new", width="stretch"):
        for k in [k for k in st.session_state if k.startswith("wp_")]:
            del st.session_state[k]
        st.session_state["t_phase"] = "plan"
        ui.to_workout(pages)


def _recent(username, pages, limit=3):
    """Finished workouts. Tap one to see every set, and repeat it if you like."""
    allsets = session_data.all_sets(username)
    sessions = training.group_sessions([x for x in allsets if x.get("day_type") != "skill"])[:limit]
    if not sessions:
        st.caption("Finished workouts show up here. Tap one to see it or do it again.")
        return
    unit = session_data.unit(username)
    for n, sess in enumerate(sessions):
        exercises = list(dict.fromkeys(x["exercise"] for x in sess["sets"]))
        ex = next((find_exercise(e.replace("Walk: ", "")) for e in exercises if find_exercise(e.replace("Walk: ", ""))), None)
        label = training.DAY_LABELS.get(sess["day_type"], "Workout")
        n_sets = len(sess["sets"])
        opened, _ = ui.tap_row(f"hist{n}", mini_url(ex) if ex else ("directions_walk" if sess["day_type"] == "cardio" else None),
                               label, f"{n_sets} set{'s' if n_sets != 1 else ''}  ·  {len(exercises)} move{'s' if len(exercises) != 1 else ''}",
                               kicker=_ago(training.days_since(sess["performed_at"])), icon=not ex)
        if opened:
            _history_dialog(username, pages, sess, unit)


@st.dialog("Workout details")
def _history_dialog(username, pages, sess, unit):
    st.markdown(f"**{training.DAY_LABELS.get(sess['day_type'], 'Workout')}**  ·  {_ago(training.days_since(sess['performed_at']))}")
    names = list(dict.fromkeys(x["exercise"] for x in sess["sets"]))
    for nm in names:
        rows = [x for x in sess["sets"] if x["exercise"] == nm]
        kind = training.kind_of(nm, sess["day_type"])
        st.markdown(f"**{nm.replace('Walk: ', '')}**")
        st.caption("  ·  ".join(training.amount(r["weight"], r["reps"], unit, kind) + (" (record)" if r["is_pr"] else "") for r in rows))
    if sess["day_type"] != "cardio" and st.button("Do it again", type="primary", icon=":material/replay:", width="stretch",
                                                  key="hist_again"):
        _start(username, pages, [n for n in names if find_exercise(n)], {}, None,
               sess["day_type"] if sess["day_type"] in ("upper", "lower", "full", "stretch", "core") else "custom")


def _open(name):
    st.session_state["lift_open"] = name


def _ago(days):
    return "today" if days == 0 else "yesterday" if days == 1 else f"{days} days ago" if days < 14 else training.break_label(days)


ROW_CSS = """<style>
/* lift rows: hairline between rows, tight spacing, the best weight is the biggest thing on the right */
[class*="st-key-keep-lift-"] { padding: .55rem 0; border-bottom: 1px solid rgba(139,92,246,.16); }
[class*="st-key-keep-lift-"] [data-testid="stMarkdownContainer"] p { margin-bottom: 0; }
[class*="st-key-keep-lift-"] button[kind="tertiary"] p { font-size: 1.05rem; font-weight: 700; letter-spacing: -.01em; white-space: nowrap; }
</style>"""


def _row(lift, unit, thumbs, sets):
    name = lift["exercise"]
    hist = _history(sets, name)
    last = f"Last {_ago(training.days_since(hist[-1]['performed_at']))}" if hist else "Not done yet"
    best = training.fmt_weight(lift["pr_weight"], unit) if lift.get("pr_weight") else "Open"
    with st.container(key=f"keep-lift-{abs(hash(name))}"):
        pic, info, act = st.columns([1, 6, 3], vertical_alignment="center")
        if thumbs.get(name):
            with pic:
                ui.thumb(thumbs[name], "sm")
        info.markdown(f"**{name}**")
        info.caption(f"{last}  ·  {lift['sets']} × {lift['rep_low']}-{lift['rep_high']} reps")
        act.button(best, key=f"open_{abs(hash(name))}", on_click=_open, args=(name,), type="tertiary",
                   icon=":material/chevron_right:", icon_position="right", help=f"Open {name}")


def _close():
    st.session_state.pop("lift_open", None)


@st.dialog("Remove this lift?")
def _confirm_remove(username, name):
    st.write(f"{name} leaves your list. Your logged workouts are kept.")
    if st.button("Yes, remove it", type="primary", key="rm_yes", width="stretch"):
        session_data.delete_lift(username, name)
        st.session_state.pop("lift_open", None)
        st.toast(f"{name} removed", icon=":material/delete:")
        st.rerun()
    if st.button("Keep it", key="rm_no", width="stretch"):
        st.rerun()


def _detail(username, lift, unit):
    name = lift["exercise"]
    sets = session_data.all_sets(username)
    hist = _history(sets, name)
    st.button("All lifts", icon=":material/arrow_back:", key="lift_back", on_click=_close)
    st.title(name)

    feels = session_data.settings(username).get("feels", {})
    days_off = training.days_since(hist[-1]["performed_at"]) if hist else 0
    sug = training.suggest(lift, training.lift_history(training.strength_sets(sets), name), days_off, unit, feel=feels.get(name))
    ex = find_exercise(name)
    gif = exercise_gif(ex) if ex else None
    left, right = st.columns([1.2, 1], vertical_alignment="center")
    with left:
        if gif:
            ui.demo(gif)
    with right:
        best = max(hist, key=lambda x: (x["weight"], x["reps"])) if hist else None
        st.metric("Best set", training.amount(lift["pr_weight"], lift["pr_reps"], unit) if lift.get("pr_weight")
                  else training.amount(best["weight"], best["reps"], unit) if best else "None yet")
        if hist:
            st.metric("Last time", training.amount(hist[-1]["weight"], hist[-1]["reps"], unit))
        if sug.get("weight"):
            import today
            st.metric("Next suggested", f"{training.fmt_weight(sug['weight'], unit)} × {sug['reps']}+",
                      delta=today.TAG_TEXT.get(sug["tag"]), delta_color="off")
    if sug.get("weight"):  # say why, in full, where the number is (a lower number always has a reason)
        st.markdown(f"**Why this number:** {sug['reason']}")
    st.caption("How it works: hit the top of your rep range on every set and the next suggestion adds weight. "
               "After 2 or more weeks off it eases you back in lighter; if something hurt, it goes lighter too.")

    st.subheader("Edit", anchor=False)
    w = st.number_input(f"Best weight ({unit})", 0.0, 2000.0, key=f"e_w_{name}", step=1.0,
                        value=round(training.to_unit(lift["pr_weight"], unit), 1) if lift.get("pr_weight") else None)
    r = st.number_input("Reps at that weight", 1, 100, value=lift.get("pr_reps") or None, key=f"e_r_{name}")
    c1, c2, c3 = st.columns(3)
    n_sets = c1.number_input("Sets", 1, 10, lift["sets"], key=f"e_s_{name}")
    lo = c2.number_input("Min reps", 1, 50, lift["rep_low"], key=f"e_lo_{name}")
    hi = c3.number_input("Max reps", 1, 50, lift["rep_high"], key=f"e_hi_{name}")
    if st.button("Save changes", type="primary", key=f"e_save_{name}", width="stretch"):
        if hi < lo:
            st.error("Max reps must be at least the min.")
        elif w and not r:
            st.error("Add the reps for that weight.")
        else:
            session_data.upsert_lift(username, name, lift["day_type"], training.from_unit(w, unit) if w else None,
                                     r if w else None, lo, hi, n_sets)
            st.toast("Saved", icon=":material/check_circle:")
            st.rerun()
    if st.button("Remove from your lifts", icon=":material/delete:", key=f"rm_{name}", width="stretch"):
        _confirm_remove(username, name)


def _add_form(username, unit):
    from exercise_data import custom_list
    names = [e["name"] for e in custom_list()] + [e["name"] for e in load_exercises()]  # your own exercises too
    exercise = st.selectbox("Exercise", names, index=None, placeholder="Search the exercise library...", key="lifts_pick")
    if not exercise:
        return
    guess = training.guess_day_type(find_exercise(exercise))
    c1, c2 = st.columns(2)
    weight = c1.number_input(f"Your best weight ({unit})", 0.0, 2000.0, value=None, placeholder="e.g. 185", key="new_pr_w", step=1.0)
    reps = c2.number_input("Reps at that weight", 1, 100, value=None, placeholder="e.g. 5", key="new_pr_r")
    day = st.pills("Counts as", DAYS, default=guess, key=f"new_dt_{exercise}", format_func=lambda d: training.DAY_LABELS[d]) or guess
    st.caption("Why we ask: your best set picks a sensible first weight. Leave it blank and the first session finds it.")
    if st.button("Add lift", type="primary", key="lifts_add", width="stretch"):
        if weight and not reps:
            st.error("Add the reps you did at that weight (even 1), or clear the weight.")
            return
        session_data.upsert_lift(username, exercise, day, training.from_unit(weight, unit) if weight else None, reps if weight else None)
        ui.forget("new_pr_", "lifts_pick", "new_dt_")
        st.toast(f"{exercise} added", icon=":material/check_circle:")
        st.rerun()
