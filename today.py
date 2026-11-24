"""Today: the home screen and the guided workout flow.

Flow (one decision per screen, nothing to configure):
    Today -> [When did you last train? (first time only)] -> Upper / Lower / Full body
          -> your lineup (4 lifts pre-picked, tap to swap) -> log sets -> finish (PR celebration)
"""
import html
import json
import time
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import streamlit as st

import celebration
import formtips
import plan as week_plan
import research
import session_data
import skills_logic as sk
import targets
import training
import ui
from exercise_data import exercise_gif, find_exercise, load_exercises, mini_url, prepare_minis, anim_url, thumb_url

LINEUP_SIZE = 4


@lru_cache(maxsize=1)
def curated():
    """Curated workouts (curated_workouts.json): each built from published guidance, cited via research ids."""
    return json.loads((Path(__file__).parent / "curated_workouts.json").read_text())["workouts"]
DAYS = [("upper", "Chest, back, shoulders, arms", "Upper body"), ("lower", "Legs and glutes", "Lower body"),
        ("full", "A bit of everything", "Full body"),
        ("custom", "Your playlists, saved exercises, or anything in the library", "Custom")]
WHEN_OPTIONS = {
    "This week": 3, "1-2 weeks ago": 10, "About a month ago": 30,
    "2-3 months ago": 75, "6+ months ago": 200,
}
TAG_TEXT = {"add": "Add weight", "reps": "Add a rep", "repeat": "Repeat", "ease": "Ease back in", "deload": "Lighter day", "start": "Starting point"}
TAG_BADGE = {
    "add": ":green-badge[Add weight]", "reps": ":blue-badge[Add a rep]", "repeat": ":gray-badge[Repeat]",
    "ease": ":orange-badge[Ease back in]", "deload": ":orange-badge[Lighter day]", "start": ":violet-badge[Starting point]",
}


def today_page(username, pages):
    summary = st.session_state.pop("t_summary", None)
    if summary:
        celebrate(username, summary, pages)

    lifts = session_data.lifts(username)
    phase = st.session_state.get("t_phase", "landing")
    if phase == "landing":
        phase = "day"
        st.session_state["t_phase"] = phase
    meant = st.session_state.pop("t_go", False) | st.session_state.pop("t_go_session", False)
    if st.session_state.get("_arrived") and not meant and phase not in ("landing", "day"):
        phase = "day"  # opened from the tab bar: always the Workouts page (the bottom bar returns to a live workout)
        st.session_state["t_phase"] = phase

    if phase == "session" and "sess" in st.session_state:
        session_view(username, pages)
    elif phase == "plan":
        plan_view(username, pages)
    elif phase == "walk":
        walk_view(username, pages)
    elif phase == "template" and st.session_state.get("t_tpl"):
        template_view(username, pages)
    elif phase == "lineup":
        lineup_view(username, pages)
    elif phase == "day":
        day_view(username, pages)
    else:
        when_view(pages)


def _go(phase, **extra):
    st.session_state.update(t_phase=phase, **extra)
    ui.to_top()


# --- step: when did you last train (only if there's no history) ---------------------
def when_view(pages):
    if st.button("Back", icon=":material/arrow_back:", key="wk_back_home"):
        st.switch_page(pages["home"])
    st.title("When did you last work out?")
    st.caption("One tap. It helps us start at a sensible weight instead of guessing.")
    for label, days in WHEN_OPTIONS.items():
        st.button(label, on_click=_go, args=("day",), kwargs={"t_days_off": days}, key=f"when_{days}")


# --- step: upper / lower / full ---------------------------------------------------------
def _global_days_off(sets):
    sessions = training.group_sessions(sets)
    if sessions:
        return training.days_since(sessions[0]["performed_at"])
    return st.session_state.get("t_days_off", 0)


def _minutes(exercises):
    """About how long: ~40 s per set plus its rest (rest lengths from research.json), rounded to 5 min."""
    secs = sum(sets * (40 + rest_seconds(name)) for name, sets in exercises)
    return max(10, int(round(secs / 300.0)) * 5)


def workout_minutes(w):
    """About how long a ready-made workout takes: lifts as in _minutes; holds are the hold (both sides when the
    stretch is one-sided) plus about 15 seconds to change position, with no lifting rest."""
    lifts = [(e[0], e[1]) for e in w["exercises"] if e[4:] != ["hold"]]
    hold_secs = sum(e[1] * (e[2] * (2 if _per_side(e[0]) else 1) + 15) for e in w["exercises"] if e[4:] == ["hold"])
    secs = sum(sets * (40 + rest_seconds(name)) for name, sets in lifts) + hold_secs
    return max(5, int(round(secs / 300.0)) * 5)


def day_view(username, pages):
    """Workouts: explore only, the same for everyone. Your own things (plan, playlists, lifts) live in Library."""
    if st.session_state.get("t_light"):
        st.info("Lighter session: about half the sets at a slightly lighter weight. It still counts as a workout day.",
                icon=":material/spa:")
        if st.button("Do the full session instead", key="wk_not_light", type="tertiary"):
            st.session_state.pop("t_light", None)
            st.rerun()
    _curated_list()


def from_lifts(username, pages):
    """Upper / Lower / Full / Custom built from the lifts you track (shown in Library > Lifts)."""
    lifts = session_data.lifts(username)
    sets = training.strength_sets(session_data.all_sets(username))
    sessions = training.group_sessions(sets)
    last_day = sessions[0]["day_type"] if sessions else None
    suggested = training.suggest_split(
        last_day, any(l["day_type"] == "upper" for l in lifts), any(l["day_type"] == "lower" for l in lifts)
    )
    cover = {"upper": "Barbell Bench Press - Medium Grip", "lower": "Barbell Squat", "full": "Barbell Deadlift"}
    for key, desc, label in DAYS:
        with st.container(key=f"keep-day-{key}"):
            pic, text, act = st.columns([1, 5, 2], vertical_alignment="center")
            if key == "custom":
                with pic:
                    ui.icon_thumb("tune")
            else:
                ex = find_exercise(cover[key])
                thumb = mini_url(ex) if ex else None
                if thumb:
                    with pic:
                        ui.thumb(thumb, "sm")
            text.markdown(f"**{label}**" + ("  :violet-badge[Suggested]" if key == suggested else ""))
            text.caption(desc)
            if act.button("Choose", key=f"day_{key}", width="stretch"):
                st.session_state.update(t_phase="lineup", t_day=key)
                ui.to_workout(pages)


def _week_section(username):
    """Your week, at the top of Workout: what's planned, or one tap to plan it."""
    plan = week_plan.get(username)
    st.subheader("Your week", anchor=False)
    if plan:
        st.html(week_plan.week_html(username, plan, training.week_dots(session_data.all_sets(username))))
        st.button("Edit my week", icon=":material/edit_calendar:", key="wk_plan_edit", on_click=_open_plan, args=(True,))
    else:
        st.caption("Pick your training days once. Then Home shows today's workout, ready to start.")
        st.button("Plan my week", icon=":material/calendar_month:", key="wk_plan_new", on_click=_open_plan)
    st.write("")


def _open_plan(edit=False):
    for k in [k for k in st.session_state if k.startswith("wp_")]:
        del st.session_state[k]  # a fresh draft from what's saved
    if edit:  # straight to the week you already have
        st.session_state["wp_step"] = 3
    _go("plan")


PLAN_STEPS = ["How many days", "Which days", "Your goal", "Your week"]


def _plan_nav(back_to):
    """Back always works: to the previous step, or out of the planner from the first one."""
    if st.button("Back", icon=":material/arrow_back:", key="wp_back"):
        if back_to is None:
            _go("day")
        else:
            st.session_state["wp_step"] = back_to
        st.rerun()


def plan_view(username, pages):
    """Plan my week as four short steps: how many days, which days, your goal, then the week to review."""
    step = int(st.session_state.get("wp_step", 0))
    settings = session_data.settings(username)
    _plan_nav(step - 1 if step else None)
    st.html('<div class="bs-seg">' + "".join(
        f'<i class="{"done" if i < step else "now" if i == step else ""}"></i>' for i in range(len(PLAN_STEPS)))
        + f'</div><p style="opacity:.7;margin:0 0 .3rem;font-size:.9rem">Step {step + 1} of {len(PLAN_STEPS)}</p>')
    st.html(SESSION_CSS)

    if step == 0:
        st.title("How many days a week do you want to train?")
        st.caption("Count walks and skill practice too. Start with what fits your life; you can change it any week.")
        if "wp_n" not in st.session_state:  # widget values vanish when their step is off screen: keep a copy (_v)
            st.session_state["wp_n"] = st.session_state.get("wp_n_v") or len(week_plan.default_days(username))
        n = st.pills("Days a week", list(range(1, 8)), key="wp_n", label_visibility="collapsed")
        st.caption({None: "Pick a number to continue.", 1: "A good start. One session a week still builds strength.",
                    2: "Enough for real progress.", 3: "A classic beginner week, with a day off between.",
                    4: "Room to train upper and lower body twice.", 5: "A busy week. Keep at least one or two easy days.",
                    6: "Lots of training. Make rest days count.", 7: "Every day. Mix in walks and easy days."}[n])
        with st.container(key="bs-donebar"):
            if st.button("Continue", type="primary", key="wp_next0", width="stretch", disabled=not n):
                if n != st.session_state.get("wp_n_v"):
                    st.session_state["wp_days_v"] = [week_plan.DAYS[d][:3] for d in week_plan.default_days(username, n)]
                st.session_state["wp_n_v"] = n
                st.session_state["wp_step"] = 1
                st.rerun()

    elif step == 1:
        n = int(st.session_state.get("wp_n_v") or 3)
        if "wp_days" not in st.session_state:
            st.session_state["wp_days"] = st.session_state.get("wp_days_v") or [
                week_plan.DAYS[d][:3] for d in week_plan.default_days(username, n)]
        st.title("Which days?")
        st.caption(f"Pick {n}. We spread them out so your muscles get a day between.")
        short = [d[:3] for d in week_plan.DAYS]
        picked = st.pills("Days", short, selection_mode="multi", key="wp_days", label_visibility="collapsed") or []
        if len(picked) != n:
            st.caption(f"{len(picked)} of {n} picked." + (" That's fine too: we'll plan the days you picked."
                                                          if picked else ""))
        with st.container(key="bs-donebar"):
            if st.button("Continue", type="primary", key="wp_next1", width="stretch", disabled=not picked):
                st.session_state["wp_days_v"] = picked
                st.session_state["wp_step"] = 2
                st.rerun()

    elif step == 2:
        st.title("What are your goals this week?")
        st.caption("Pick as many as you like. The first one you pick decides your main days; the others add light "
                   "extras like a walk or a stretch on free days.")
        if "wp_goals" not in st.session_state:
            st.session_state["wp_goals"] = st.session_state.get("wp_goals_v") or week_plan.default_goals(username)
        gids = list(week_plan.GOALS)
        goals = st.pills("Goals", gids, selection_mode="multi", key="wp_goals", label_visibility="collapsed",
                         format_func=lambda g: week_plan.GOALS[g][0]) or []
        for g in goals:
            st.caption(f"**{week_plan.GOALS[g][0]}:** {week_plan.GOALS[g][1]}")
        with st.container(key="bs-donebar"):
            if st.button("See my week", type="primary", key="wp_next2", width="stretch", disabled=not goals):
                days = [[d[:3] for d in week_plan.DAYS].index(x) for x in st.session_state.get("wp_days_v") or []]
                st.session_state["wp_goals_v"] = list(goals)
                draft = week_plan.suggest(username, days, list(goals))
                for d in range(7):
                    st.session_state[f"wp_{d}"] = draft.get(str(d), week_plan.REST)
                st.session_state["wp_step"] = 3
                st.rerun()

    else:
        goals = st.session_state.get("wp_goals_v") or week_plan.default_goals(username)
        st.title("Your week")
        st.caption("Goals: " + ", ".join(week_plan.GOALS[g][0] for g in goals)
                   + ". Change any day, or open it to see and edit the workout.")
        if st.button("Clear", icon=":material/clear_all:", key="wp_restart", type="tertiary", help="Set every day to Rest"):
            for d in range(7):
                st.session_state[f"wp_{d}"] = week_plan.REST
            st.rerun()
        opts = week_plan.options(username)
        labels = dict(opts)
        for d, name in enumerate(week_plan.DAYS):
            k = f"wp_{d}"
            if k not in st.session_state:  # an unsaved draft first (back from editing a day), else the saved week
                st.session_state[k] = (st.session_state.get("wp_draft") or {}).get(str(d)) or \
                    week_plan.get(username).get(str(d), week_plan.REST)
            if st.session_state[k] not in labels:  # a playlist just made from this day
                opts, labels = week_plan.options(username), dict(week_plan.options(username))
            st.selectbox(name, [o for o, _ in opts], format_func=lambda o: labels.get(o, "Rest"), key=k)
            got = week_plan.contents(username, st.session_state[k]) if st.session_state[k] != week_plan.REST else None
            if got:  # plan it fully: see the moves, change them, keep it as your own version of this day
                names, _, _ = got
                c1, c2 = st.columns([3, 1.4], vertical_alignment="center")
                c1.caption(", ".join(n.replace("Skill: ", "") for n in names[:4]) + ("..." if len(names) > 4 else ""))
                if c2.button("See and edit", key=f"wp_edit_{d}", width="stretch"):
                    _edit_day(username, pages, d, st.session_state[k])
        chosen = {str(d): st.session_state[f"wp_{d}"] for d in range(7)}
        skills = week_plan._active_skills(username)
        if skills:  # a skill practice on top of a workout day
            lift_days = [d for d in range(7) if week_plan.contents(username, chosen[str(d)]) if chosen[str(d)] != week_plan.REST]
            saved = session_data.settings(username).get("week_skill") or {}
            sid = skills[0][0]
            st.markdown(f"##### Add {skills[0][1]['title']} practice to a workout day")
            st.caption("It runs after the workout, as one session (about 5 more minutes).")
            if "wp_skilldays" not in st.session_state:
                back = st.session_state.get("wp_skilldays_v")
                st.session_state["wp_skilldays"] = [d for d in (back if back is not None else
                                                                [d for d in lift_days if saved.get(str(d))]) if d in lift_days]
            st.pills("Skill days", lift_days, selection_mode="multi", key="wp_skilldays", label_visibility="collapsed",
                     format_func=lambda d: week_plan.DAYS[d][:3])
        # walking habit: on top of whatever else a day holds (a workout, a skill practice, or rest)
        st.markdown("##### Walking habit")
        habit = week_plan.walk_habit(username) or {}
        if "wp_walk_steps" not in st.session_state:
            back = st.session_state.get("wp_walk_v") or {}
            steps0 = back.get("steps", habit.get("steps"))
            st.session_state["wp_walk_steps"] = f"{steps0:,}" if steps0 else "Off"
            st.session_state["wp_walk_days"] = back.get("days", habit.get("days", [0, 2, 4, 5]))
        st.select_slider("Steps a day", week_plan.STEP_CHOICES, key="wp_walk_steps")
        if st.session_state["wp_walk_steps"] != "Off":
            st.pills("On these days", list(range(7)), selection_mode="multi", key="wp_walk_days",
                     format_func=lambda d: week_plan.DAYS[d][:3])
            st.caption("It goes on top of that day's plan, so a day can be a workout, a skill practice and a walk. "
                       "Home shows it to tick off. " + (research.do("steps-mortality") or ""))
        st.markdown("##### How to use this plan")
        for g in goals:
            for rid in week_plan.GOALS[g][2]:
                line = research.do(rid)
                if line:
                    st.caption(line)
        mins = week_plan.walk_minutes(chosen)
        if mins:
            st.caption(f"This week has about {mins} walking minutes. The guideline is 150 to 300; over 250 is where "
                       "studies saw clear weight loss.")
        n = sum(1 for v in chosen.values() if v != week_plan.REST)
        # "Go to Home" stays until you leave, unless you change a day again (then it's Save my week again)
        unchanged = {k: v for k, v in chosen.items() if v != week_plan.REST} == week_plan.get(username)
        just_saved = st.session_state.get("wp_saved", False) and unchanged
        if st.session_state.pop("wp_popup", False):
            _week_dialog(username, pages, chosen, n)
        with st.container(key="bs-donebar"):
            if just_saved:
                if st.button("Go to Home", type="primary", icon=":material/home:", key="wp_home", width="stretch"):
                    st.session_state.pop("wp_saved", None)
                    st.switch_page(pages["home"])
            elif st.button("Save my week", type="primary", icon=":material/check:", key="wp_save", width="stretch"):
                week_plan.save(username, chosen)
                if skills:
                    days = st.session_state.get("wp_skilldays") or []
                    session_data.save_settings(username, week_skill={str(d): f"sk:{sid}" for d in days})
                steps = st.session_state.get("wp_walk_steps", "Off")
                session_data.save_settings(username, walk_habit=(
                    {"steps": int(steps.replace(",", "")), "days": sorted(st.session_state.get("wp_walk_days") or [])}
                    if steps != "Off" else None))
                st.session_state.pop("wp_walk_v", None)
                session_data.save_settings(username, plan_goal=list(goals), weekly_goal=max(1, n))
                st.session_state.pop("wp_draft", None)
                st.session_state.pop("wp_skilldays_v", None)
                st.session_state["wp_saved"] = True
                st.session_state["wp_popup"] = True
                st.rerun()


@st.dialog(" ")
def _week_dialog(username, pages, chosen, n):
    """The moment the week is saved: its days' pictures stack in, a tick, then where to go next."""
    imgs = [week_plan.mini(username, v) for v in chosen.values() if v != week_plan.REST]
    ui.created("Your week is planned", f"{n} day{'s' if n != 1 else ''} this week", imgs)
    st.caption("Home shows today's workout, ready to start. You can change any day later from Home.")
    if st.button("Go to Home", type="primary", icon=":material/home:", key="wpd_home", width="stretch"):
        st.session_state.pop("wp_saved", None)
        ui.go("home")
    if st.button("Keep editing", key="wpd_stay", width="stretch"):
        st.rerun()


def _edit_day(username, pages, day, key):
    """Open this day's workout in the playlist editor (same screen as New playlist). Saving makes it your own
    playlist, puts it on this day, and comes back to the planner."""
    import playlist_builder

    # widget values are forgotten while you're on another page: keep the unsaved week to come back to
    st.session_state["wp_draft"] = {str(d): st.session_state.get(f"wp_{d}", week_plan.REST) for d in range(7)}
    st.session_state["wp_skilldays_v"] = st.session_state.get("wp_skilldays")
    steps = st.session_state.get("wp_walk_steps", "Off")
    st.session_state["wp_walk_v"] = {"steps": int(steps.replace(",", "")) if steps != "Off" else None,
                                     "days": st.session_state.get("wp_walk_days") or []}
    names, tpl, title = week_plan.contents(username, key)
    playlist_builder.start(username, picked=[n for n in names if not n.startswith("Skill: ")],
                           name=f"{title} ({week_plan.DAYS[day][:3]})",
                           amounts={n: [int(t.get("sets") or 3), int(t.get("rep_low") or 10)] for n, t in tpl.items()},
                           back_to_plan=day)
    st.switch_page(pages["lifts"])


@st.fragment(run_every=1)
def _walk_clock():
    w = st.session_state.get("t_walk_run") or {}
    secs = int(w.get("acc", 0) + (time.time() - w["t0"] if w.get("t0") else 0))
    st.html(f"<div class='bs-rest'><div class='bs-rest-n'>{secs // 60}:{secs % 60:02d}</div>"
            f"<div class='bs-rest-l'>{'Walking' if w.get('t0') else 'Paused' if secs else 'Ready when you are'}</div></div>")


def walk_view(username, pages):
    """A walk: a clock you can start and pause (or skip, if you walked without it), then minutes logged."""
    import plan as wp

    st.session_state["_focus_mode"] = True
    st.html(SESSION_CSS + "<style>.bs-rest{text-align:center;padding:1.2rem 0}.bs-rest-n{font-size:4rem;font-weight:800;"
            "letter-spacing:-.03em;background:var(--bs-grad);-webkit-background-clip:text;background-clip:text;"
            "color:transparent}.bs-rest-l{opacity:.75}</style>")
    kind = st.session_state.get("t_walk", "brisk")
    title, meta, steps = wp.WALKS.get(kind, wp.WALKS["brisk"])
    if st.button("Back", icon=":material/arrow_back:", key="walk_back"):
        st.session_state.pop("t_walk_run", None)
        st.switch_page(pages["home"])
    st.title(title)
    st.caption(meta)
    ex = find_exercise(wp.WALK_PICTURE.get(kind, "Walking, Treadmill"))
    gif = exercise_gif(ex) if ex else None
    if gif:
        ui.demo(gif)
    ui.tracklist([(None, a, b) for a, b in steps])
    run = st.session_state.setdefault("t_walk_run", {"acc": 0.0, "t0": None})
    _walk_clock()
    a, b = st.columns(2)
    if run["t0"]:
        if a.button("Pause", icon=":material/pause:", key="walk_pause", width="stretch"):
            run["acc"] += time.time() - run["t0"]
            run["t0"] = None
            st.rerun()
    elif a.button("Start" if not run["acc"] else "Resume", icon=":material/play_arrow:", key="walk_go", width="stretch"):
        run["t0"] = time.time()
        st.rerun()
    timed = int(round((run["acc"] + (time.time() - run["t0"] if run["t0"] else 0)) / 60))
    mins = b.number_input("Minutes walked", 1, 300, max(1, timed) if timed else 30, key=f"walk_min_{timed}",
                          help="Walked without the clock? Just set the minutes.")
    if kind == "incline":
        e = research.get("incline-walk-12330")
        if e:
            st.caption(f"{e['claim']} ([source]({e['source']}))")
    with st.container(key="bs-donebar"):
        if st.button("Finish walk", type="primary", icon=":material/flag:", key="walk_done", width="stretch"):
            first = not session_data.all_sets(username)
            session_data.log_sets(username, uuid.uuid4().hex, datetime.now().isoformat(timespec="seconds"), "cardio",
                                  [{"exercise": f"Walk: {title}", "set_no": 1, "weight": 0.0, "reps": int(mins), "is_pr": False}])
            week, _ = training.streak_summary(session_data.all_sets(username))
            walked = sum(int(x["reps"]) for x in session_data.all_sets(username) if x.get("day_type") == "cardio"
                         and training.days_since(x["performed_at"]) < 7)
            st.session_state.pop("t_walk_run", None)
            st.session_state.update(t_phase="landing", t_summary={
                "unit": session_data.unit(username), "tier": "big" if first else "none", "prs": [], "sets": 0,
                "volume": 0, "reps": 0, "minutes": int(mins), "names": [], "source": title, "first_ever": first,
                "milestones": [], "week": week, "next": "full", "day": "cardio",
                "extra": [("Minutes this week", walked), ("Days this week", week)]})
            st.rerun()


EXPLORE_ROWS = [  # (row title, which workouts); a workout can sit in more than one row. Rows need 3+ to show.
    ("Built for a result", lambda w, m: bool(w.get("goal"))),
    ("About an hour at the gym", lambda w, m: m >= 50),
    ("At home", lambda w, m: w.get("place") == "home" and w["focus"] not in ("stretch", "core") and not w.get("goal")),
    ("At the gym", lambda w, m: w.get("place") == "gym"),
    ("Push, pull and legs", lambda w, m: w.get("tag") in ("push", "pull", "legs")),
    ("Arms, shoulders and glutes", lambda w, m: w.get("tag") in ("arms", "shoulders", "glutes")),
    ("Full body", lambda w, m: w["focus"] == "full"),
    ("Stretch, mobility and core", lambda w, m: w["focus"] in ("stretch", "core")),
    ("20 minutes or less", lambda w, m: m <= 20),
]
MIN_ROW = 3
TINT = {"full": "124,58,237", "upper": "37,99,235", "lower": "219,39,119", "stretch": "13,148,136", "core": "234,88,12",
        "push": "37,99,235", "pull": "79,70,229", "legs": "219,39,119", "glutes": "225,29,72", "arms": "217,119,6",
        "shoulders": "8,145,178", "cardio": "220,38,38"}
TILE_CSS = """<style>
[class*="st-key-hrow-"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; overflow-x: auto; gap: 12px !important;
  scroll-snap-type: x mandatory; padding: 2px 2px 10px; scrollbar-width: none; }
[class*="st-key-hrow-"] [data-testid="stHorizontalBlock"]::-webkit-scrollbar { display: none; }
[class*="st-key-hrow-"] [data-testid="stColumn"] { flex: 0 0 158px !important; width: 158px !important; min-width: 158px !important;
  position: relative; scroll-snap-align: start; }
[class*="st-key-hrow-"] [data-testid="stColumn"] [data-testid="stElementContainer"]:has(.stButton) { position: absolute; inset: 0; z-index: 2; margin: 0;
  width: 100% !important; height: 100% !important; }
[class*="st-key-hrow-"] [data-testid="stColumn"] .stButton { position: absolute; inset: 0; max-width: none !important; width: 100% !important; height: 100% !important; }
[class*="st-key-hrow-"] [data-testid="stColumn"] .stButton button { width: 100% !important; height: 100%; opacity: 0; cursor: pointer; }
[class*="st-key-hrow-"] [data-testid="stColumn"]:has(button:focus-visible) .bs-wt { outline: 3px solid #7C3AED; outline-offset: 2px; }
[class*="st-key-hrow-"] [data-testid="stColumn"]:hover .bs-wt { transform: translateY(-2px); }
.bs-wt { position: relative; width: 158px; height: 206px; border-radius: 20px; overflow: hidden; transition: transform .15s ease;
  background: var(--tint-solid); box-shadow: 0 6px 18px rgba(30,20,60,.14); }
.bs-wt img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; }
.bs-wt::after { content: ""; position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(var(--tint),.10) 0%, rgba(var(--tint),.25) 40%, rgba(16,10,34,.92) 100%); }
.bs-wt .tx { position: absolute; left: 12px; right: 12px; bottom: 12px; z-index: 1; color: #fff; }
.bs-wt .t { font-weight: 700; font-size: 1rem; line-height: 1.2; letter-spacing: -.01em; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden; }
.bs-wt .m { font-size: .76rem; opacity: .85; margin-top: .25rem; }
.bs-wt .chip { position: absolute; top: 10px; left: 10px; z-index: 1; font-size: .68rem; font-weight: 650; letter-spacing: .04em;
  color: #fff; background: rgba(var(--tint),.85); padding: .18rem .5rem; border-radius: 999px; }
.bs-rowh { font-weight: 650; font-size: 1.05rem; margin: .6rem 0 .5rem; }
.st-key-keep-wk-head [data-testid="stHorizontalBlock"] { justify-content: space-between; }
.st-key-keep-wk-head [data-testid="stColumn"]:first-child { flex: 1 1 auto !important; }
.st-key-keep-wk-head [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; display: flex; justify-content: flex-end; }
.st-key-keep-wk-head button span[data-testid="stIconMaterial"] { font-size: 28px; }
</style>"""
FOCUS_CHIP = {"full": "Full body", "upper": "Upper", "lower": "Lower", "stretch": "Stretch", "core": "Core", "push": "Push",
              "pull": "Pull", "legs": "Legs", "glutes": "Glutes", "arms": "Arms", "shoulders": "Shoulders", "cardio": "Cardio"}


def cover_url(w):
    """The workout's picture: its chosen cover exercise (curated_workouts.json "cover"), else its first move."""
    ex = find_exercise(w.get("cover") or w["exercises"][0][0]) or find_exercise(w["exercises"][0][0])
    return anim_url(ex, labels=False) if ex else ""


def _open_tpl(wid):
    _go("template", t_tpl=wid)


def _tile_row(key, title, items):
    """A row of workout tiles that scrolls sideways; the whole tile is the button."""
    st.html(f'<div class="bs-rowh">{html.escape(title)}</div>')
    with st.container(key=f"hrow-{key}"):
        cols = st.columns(len(items))
        for col, (w, mins) in zip(cols, items):
            pic = cover_url(w)
            equip = "No equipment" if w["equipment"] == "None" else w["equipment"]
            kind = w["focus"] if w.get("tag") in (None, "results") else w["tag"]
            tint = TINT.get(kind, TINT["full"])
            col.html(f'<div class="bs-wt" style="--tint:{tint};--tint-solid:rgb({tint})">'
                     + (f'<img src="{html.escape(pic)}" alt="" loading="lazy">' if pic else "")
                     + f'<span class="chip">{FOCUS_CHIP.get(kind, "Workout")}</span>'
                     f'<div class="tx"><div class="t">{html.escape(w["title"])}</div>'
                     f'<div class="m">{mins} min · {html.escape(equip)}</div></div></div>')
            col.button(f"Open {w['title']}", key=f"tpl_{key}_{w['id']}", on_click=_open_tpl, args=(w["id"],))


def _curated_list():
    """Explore: search, then rows of ready-made workouts by type. Each opens a preview you can edit."""
    st.html(TILE_CSS)
    with st.container(key="keep-wk-head"):
        t, b = st.columns([5, 1], vertical_alignment="center")
        t.title("Workouts")
        if b.button("", icon=":material/close:" if st.session_state.get("wk_search_open") else ":material/search:",
                    key="wk_search_btn", help="Search workouts", type="tertiary"):
            st.session_state["wk_search_open"] = not st.session_state.get("wk_search_open")
            st.session_state.pop("wk_search", None)
            st.rerun()
    q = ""
    if st.session_state.get("wk_search_open"):
        q = st.text_input("Search", placeholder="Workout or exercise, e.g. plank, legs, stretch",
                          key="wk_search", label_visibility="collapsed").strip().lower()
    all_w = [(w, workout_minutes(w)) for w in curated()]
    if q:
        hits = [(w, m) for w, m in all_w if q in w["title"].lower() or q in w["focus"] or q in w["blurb"].lower()
                or any(q in e[0].lower() for e in w["exercises"])
                or (q in ("legs", "leg") and w["focus"] == "lower") or (q in ("arms", "chest", "back") and w["focus"] == "upper")]
        if hits:
            _tile_row("search", f"{len(hits)} workout{'s' if len(hits) != 1 else ''} for \"{q}\"", hits)
        else:
            st.caption("No workouts match. Try another word, like stretch, core or upper.")
        return
    for i, (title, test) in enumerate(EXPLORE_ROWS):
        items = [(w, m) for w, m in all_w if test(w, m)]
        if len(items) >= MIN_ROW:  # a row of one or two looks unfinished; those workouts sit in other rows
            _tile_row(f"r{i}", title, items)
    st.caption("Built on published training guidance. Open one to see why it works, and change anything.")


def _start_template(username, w):
    st.session_state["t_template"] = {e[0]: {"sets": e[1], "rep_low": e[2], "rep_high": e[3],
                                             "hold": len(e) > 4 and e[4] == "hold"} for e in w["exercises"]}
    st.session_state["t_day"] = w["focus"] if w["focus"] in ("upper", "lower", "full", "stretch", "core") else "full"
    st.session_state["t_source"] = w["title"]
    _begin(username, [e[0] for e in w["exercises"]])


def _save_template(username, w, name=None):
    name = (name or w["title"]).strip()
    have = set(session_data.routines(username))
    if name not in have:
        for ex, sets, lo, hi, *_ in w["exercises"]:
            session_data.add_routine(username, name, [ex], sets, lo, _minutes([(ex, sets)]))
    st.session_state["t_just_saved"] = name


@st.dialog("Save as a playlist")
def _save_dialog(username, w):
    """Name it first (it's how you'll find it in Library and pick it for a day)."""
    name = st.text_input("Name", value=w["title"], key="tpl_save_name", max_chars=40)
    taken = name.strip() in session_data.routines(username)
    if taken:
        st.caption("You already have a playlist with that name.")
    if st.button("Save", type="primary", icon=":material/bookmark_add:", width="stretch", key="tpl_save_ok",
                 disabled=not name.strip() or taken):
        _save_template(username, w, name)
        st.rerun()


def _tpl_back(pages):
    if st.session_state.get("t_tpl_from") == "home":  # opened from Home or the welcome screen
        if st.button("Back", icon=":material/arrow_back:", key="tpl_back_home"):
            st.session_state.pop("t_tpl_from", None)
            _go("landing")
            st.switch_page(pages["home"])
    else:
        st.button("All workouts", icon=":material/arrow_back:", on_click=_go, args=("day",), key="tpl_back")


def template_view(username, pages):
    base = next((x for x in curated() if x["id"] == st.session_state.get("t_tpl")), None)
    if not base:
        _go("day")
        st.rerun()
    w = base
    unit = session_data.unit(username)
    _tpl_back(pages)
    names = [e[0] for e in w["exercises"]]
    ui.hero(w["level"], w["title"], f"{len(names)} moves  ·  about {workout_minutes(w)} min  ·  "
            f"{w['equipment'] if w['equipment'] != 'None' else 'no equipment'}", cover_url(base) or None)
    st.write("")
    st.markdown(w["blurb"])
    if base.get("goal"):
        _goal_card(username, base, pages)
    minis = prepare_minis([e for e in (find_exercise(n) for n in names) if e])
    lifts = {l["exercise"]: l for l in session_data.lifts(username)}
    rows = []
    for name, sets, lo, hi, *kind in w["exercises"]:
        best = lifts.get(name, {}).get("pr_weight")
        amount = f"{sets} × {lo} s hold" if kind == ["hold"] else f"{sets} × {lo}-{hi} reps"
        rows.append((minis.get(name), name, amount + (f"  ·  your best {training.fmt_weight(best, unit)}" if best else ""),
                     targets.works(name)))
    ui.tracklist(rows)
    st.caption("To change it just for today, tap Start: the next page lets you edit everything before the clock "
               "starts. To keep your own version, tap Edit.")
    with st.container(key="keep-tpl-actions"):
        a, b = st.columns(2)
        if a.button("Edit", icon=":material/edit:", key="tpl_edit", width="stretch",
                    help="Opens the same editor as your playlists. Saving keeps it as your own version."):
            import playlist_builder
            playlist_builder.start(username, picked=names, name=f"{base['title']} (my version)",
                                   amounts={e[0]: [int(e[1]), int(e[2])] for e in base["exercises"]})
            st.switch_page(pages["lifts"])
        if b.button("Save as playlist", icon=":material/bookmark_add:", key="tpl_save", width="stretch"):
            _save_dialog(username, w)
    just = st.session_state.pop("t_just_saved", None)
    if just:
        ui.saved(f"Saved as {just}", "It's in Library > Playlists, ready to start or put on any day.",
                 [minis.get(n) for n in names])
    note = targets.goal_note(base)
    if note:
        _for_goal(note)
    st.markdown("##### Why it works")
    for rid in dict.fromkeys(w.get("research", []) + (note["research"] + note["expect"]["research"] if note else [])):
        e = research.get(rid)
        if e and e.get("source") and e.get("status") != "unverified":
            link = "summary" if e["status"] == "secondary" else "source"  # a summary article, not the study itself
            st.caption(f"{e['claim']} ([{link}]({e['source']}))")
    st.caption("This routine is built from that guidance. The exact routine has not itself been tested in a study.")
    st.html(SESSION_CSS)
    with st.container(key="bs-donebar"):
        if st.button("Start this workout", type="primary", icon=":material/play_arrow:", key="tpl_go", width="stretch"):
            st.session_state.pop("t_tpl_from", None)
            _start_template(username, w)
            st.rerun()


GOAL_CSS = """<style>
.bs-goal { border-radius: 16px; padding: 14px 16px; margin: 4px 0 10px; background: var(--bs-accent-soft); }
.bs-goal .k { font-size: .72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--bs-accent-ink); }
.bs-goal .g { font-size: 1.05rem; font-weight: 700; margin: 2px 0 10px; }
.bs-goal ul { margin: 0; padding-left: 1.1rem; } .bs-goal li { margin: 3px 0; line-height: 1.35; }
.bs-goal .e { font-size: .86rem; opacity: .85; margin: 10px 0 0; line-height: 1.4; }
</style>"""


def _goal_card(username, w, pages):
    """What a result program is for, how often to show up, and what to honestly expect."""
    from html import escape

    lines = [w["schedule"]] + ([w["also"]] if w.get("also") else [])
    st.html(GOAL_CSS + f'<div class="bs-goal"><div class="k">Goal</div><div class="g">{escape(w["goal"])}</div><ul>'
            + "".join(f"<li>{escape(x)}</li>" for x in lines)
            + "<li>Missed a day? Pick the next free one. Showing up 3 times a week is what counts, not which days.</li>"
            + f'</ul><p class="e">{escape(w["expect"])}</p></div>')
    if w.get("skill"):
        lad = sk.all_ladders(session_data.custom_skills(username)).get(w["skill"])
        if lad and st.button(f"See the {lad['title']} steps in Skills", icon=":material/trending_up:",
                             key="tpl_skill", width="stretch"):
            mine = w["skill"] in session_data.skills(username)
            st.session_state["sk_view"] = ("skill" if mine else "about", w["skill"])
            st.switch_page(pages["skills"])


def _for_goal(note):
    """What this workout can and can't do for the goal it's named for, and when to expect change (targets.goal_note).
    Every line here is backed by the sources listed under it in Why it works."""
    st.markdown("##### For your goal")
    st.markdown(f"**{note['title']}**\n\n" + "\n".join(f"- {x}" for x in note["lines"]))
    if note["tip"]:
        st.markdown(f"**For this workout:** {note['tip']}")
    st.caption("  ".join(note["expect"]["lines"]))


def _pick_day(day):
    _go("lineup", t_day=day)  # keep any lineup the person already chose for this day


# --- step: your lineup -------------------------------------------------------------------
def _virtual_lift(name):
    ex = find_exercise(name)
    return {"exercise": name, "day_type": training.guess_day_type(ex) if ex else "upper", "pr_weight": None,
            "pr_reps": None, "rep_low": 8, "rep_high": 12, "sets": 3}


def _plan(username, names):
    unit = session_data.unit(username)
    lifts = {l["exercise"]: l for l in session_data.lifts(username)}
    sets = training.strength_sets(session_data.all_sets(username))
    sessions = training.group_sessions(sets)
    feels = session_data.settings(username).get("feels", {})
    plan = []
    tpl = st.session_state.get("t_template") or {}
    for name in names:
        lift = lifts.get(name) or _virtual_lift(name)  # anything from the library can be trained
        if name in tpl:  # a curated workout or saved routine sets its own sets and rep range
            lift = {**lift, **tpl[name]}
        history = training.lift_history(sets, name)
        if history:
            days_off = training.days_since(history[0]["performed_at"])
        elif sessions:
            days_off = training.days_since(sessions[0]["performed_at"])
        else:
            days_off = st.session_state.get("t_days_off", 0)
        plan.append((lift, training.suggest(lift, history, days_off, unit, feel=feels.get(name))))
    return plan


def lineup_view(username, pages):
    """A day type was picked (Upper, Lower, Full, Build your own). If a workout is already going, offer to resume it
    first; otherwise pick today's lifts and open the ready page, where everything can be changed."""
    day = st.session_state.get("t_day", "full")
    lifts = session_data.lifts(username)
    if "sess" in st.session_state:
        sess = st.session_state["sess"]
        n_done = sum(1 for i in sess["items"] for r in i["rows"] if r["d"])
        st.button("Back", icon=":material/arrow_back:", on_click=_go, args=("day",))
        st.title("You have a workout going", anchor=False)
        st.caption(f"{sess.get('source') or 'Workout'}  ·  {n_done} set{'s' if n_done != 1 else ''} logged. "
                   "Nothing is lost if you resume.")
        if st.button("Start a new one instead", icon=":material/restart_alt:", key="wk_new",
                     help="This replaces the workout in progress."):
            st.session_state.pop("sess", None)
            session_data.clear_live(username)
            st.rerun()
        st.html(SESSION_CSS)
        with st.container(key="bs-donebar"):
            if st.button("Resume workout", type="primary", icon=":material/play_arrow:", key="wk_resume", width="stretch"):
                _go("session")
                st.rerun()
        return
    pool = lifts if day in ("full", "custom") else [l for l in lifts if l["day_type"] in (day, "core")]
    chosen = [n for n in training.pick_lineup(lifts, "full" if day == "custom" else day, session_data.all_sets(username),
                                              LINEUP_SIZE) if n in {l["exercise"] for l in pool}]
    chosen += [n for n in st.session_state.pop("t_extras", []) if n not in chosen]
    if day == "custom":
        st.session_state.setdefault("t_source", "Your lifts")
    _begin(username, chosen)
    st.rerun()


def _expand_skill_blocks(username, chosen):
    """'Skill: <id>' in a playlist becomes that skill's drills and then your current step, in place. Each part gets
    its own name, picture (library demo) and target; the step is tagged so finishing it counts as a practice."""
    if not any(n.startswith("Skill: ") for n in chosen):
        return chosen, {}
    ladders = sk.all_ladders(session_data.custom_skills(username))
    states = session_data.skills(username)
    out, tpl = [], {}
    for n in chosen:
        lad = ladders.get(n[7:]) if n.startswith("Skill: ") else None
        if not n.startswith("Skill: "):
            out.append(n)
            continue
        if not lad or n[7:] not in states:
            continue
        i = min(states[n[7:]]["step"], len(lad["steps"]) - 1)
        parts = [(d, False) for d in (lad.get("drills") or [])] + [(lad["steps"][i], True)]
        for part, is_step in parts:
            label = part["name"] if part["name"] not in out else f"{part['name']} ({lad['title']})"
            out.append(label)
            tpl[label] = {"sets": int(part["sets"]), "rep_low": int(part["target"]), "rep_high": int(part["target"]),
                          "hold": part.get("kind") == "hold", "media": part.get("library"), "skill_part": lad["id"],
                          "per_side": bool(part.get("per_side")),
                          **({"skill": lad["id"]} if is_step else {})}
    return out, tpl


def _make_items(username, chosen):
    """Session items for these exercise names: today's suggested sets, reps and weight for each."""
    unit = session_data.unit(username)
    sets = session_data.all_sets(username)
    items = []
    light = bool(st.session_state.pop("t_light", False))  # "Not feeling it today": half the sets, a bit lighter
    mine = session_data.settings(username).get("ex_prefs") or {}  # your own hold times and sets, remembered
    for lift, sug in _plan(username, chosen):
        pref = mine.get(lift["exercise"]) or {}
        if lift.get("hold"):  # a stretch or plank: hold for the time, no reps or weight to beat
            sug = {**sug, "weight": None, "reps": int(pref.get("target") or lift.get("rep_low") or 30), "tag": "repeat",
                   "reason": "Ease in, breathe, and hold. Mild tension is right; stop if it hurts."}
        elif lift.get("skill_part") or lift.get("phase"):  # skill parts, warm-up moves: own target, no weight
            sug = {**sug, "weight": None, "reps": int(lift.get("rep_low") or 5), "tag": "repeat",
                   "reason": "Part of your skill practice. Hit the target on every set to count it toward moving up."}
        if pref.get("sets"):
            sug = {**sug, "sets": int(pref["sets"])}
        elif sug["tag"] == "start" and not sug["weight"] and is_bodyweight(lift["exercise"]):
            sug = {**sug, "reason": "First time: do as many reps as you can with good form, then log them."}
        w = float(round(training.to_unit(sug["weight"], unit), 1)) if sug["weight"] else 0.0
        if light:
            w = float(round(w * 0.9)) if w else 0.0
            sug = {**sug, "sets": max(1, (sug["sets"] + 1) // 2), "reason": "Lighter day: fewer sets, a little lighter."}
        items.append({
            "uid": uuid.uuid4().hex[:8], "exercise": lift["exercise"], "lift": lift, "sug": sug, "step": float(training.step(lift["day_type"], unit)),
            "prev": [s for s in sets if s["exercise"] == lift["exercise"]],
            "rows": [{"w": w, "r": sug["reps"], "d": False} for _ in range(sug["sets"])],
        })
    return items


def _begin(username, chosen):
    """Set up a workout and open its ready page: what's in it, a warm-up offer, and an editable plan.
    The clock starts only when you tap Start workout."""
    chosen, block_tpl = _expand_skill_blocks(username, chosen)
    if block_tpl:
        st.session_state["t_template"] = {**(st.session_state.get("t_template") or {}), **block_tpl}
    items = _make_items(username, chosen)
    st.session_state["sess"] = {
        "id": uuid.uuid4().hex, "day": st.session_state.get("t_day", "full"), "unit": session_data.unit(username),
        "started": None, "ready": True, "items": items, "notified": set(),
        "source": st.session_state.pop("t_source", None),
        "from": st.session_state.pop("t_from_page", None),  # where it was started: Back and Done return there
    }
    st.session_state.pop("t_template", None)
    for k in [k for k in st.session_state if str(k).startswith("pe:")]:
        del st.session_state[k]
    st.session_state["t_phase"] = "session"
    st.session_state["t_go_session"] = True
    ui.to_top()
    session_data.save_live(username, st.session_state["sess"])


# --- logging: one exercise at a time ------------------------------------------------------------
# "Go easy on" areas from onboarding, matched to the exercise library's muscles and categories.
AREA_MUSCLES = {"Knee": {"quadriceps"}, "Shoulder": {"shoulders"}, "Lower back": {"lower back"}, "Wrist": {"forearms"},
                "Hip": {"abductors", "adductors", "glutes"}, "Ankle": {"calves"}, "Neck": {"neck"}}
JUMPY = {"Knee", "Ankle"}  # jumping (plyometric) moves load these most


def easy_on(name, areas):
    """Which of the person's flagged areas this exercise loads, as words ('knee and ankle'), or ''."""
    ex = find_exercise(name) or {}
    muscles = set(ex.get("primaryMuscles") or []) | set(ex.get("secondaryMuscles") or [])
    hit = [a.lower() for a in areas
           if muscles & AREA_MUSCLES.get(a, set()) or (a in JUMPY and ex.get("category") == "plyometrics")
           or (a == "Wrist" and any(w in name.lower() for w in ("push", "plank", "handstand")))]
    return " and ".join(hit)


def rest_seconds(name):
    """Rest by exercise type: heavy barbell compounds longer, bodyweight shorter (see research.json)."""
    ex = find_exercise(name) or {}
    if ex.get("category") == "stretching":  # a stretch or mobility move: just change position and go on
        return 15
    eq = (ex.get("equipment") or "body only").lower()
    if eq in ("body only", "none", "other"):
        return 60
    return 150 if (ex.get("mechanic") == "compound" and eq == "barbell") else 90


amount = training.amount


def _best_hold(item):
    return max([int(s_["reps"]) for s_ in item["prev"]] or [0])


def _media_name(item):
    """The library exercise whose demo shows this item (a skill drill keeps its own name, the library's picture)."""
    return (item or {}).get("lift", {}).get("media") or (item or {}).get("exercise", "")


def _no_weight(item):
    lift = (item or {}).get("lift", {})
    return bool(lift.get("skill_part") or lift.get("phase"))


def _is_hold(item):
    return bool((item or {}).get("lift", {}).get("hold"))


def _per_side(name):
    n = name.lower()
    return any(w in n for w in ("side", "one ", "single", "lying crossover", "knee across", "runner", "dancer", "quad",
                                "hip flexor", "calf stretch", "glute"))


def is_bodyweight(name):
    ex = find_exercise(name) or {}
    return (ex.get("equipment") or "body only").lower() in ("body only", "none")


FEEL_KEY = {"Easy": "easy", "Just right": "right", "Hard": "hard", "Pain": "pain"}
FEEL_LABEL = {v: k for k, v in FEEL_KEY.items()}


def _item(sess, uid):
    return next(x for x in sess["items"] if x["uid"] == uid)


def _current(sess):
    """The exercise you're on: the one you jumped to, else the first with sets left."""
    focus = sess.get("focus")
    for it in sess["items"]:
        if it["uid"] == focus and any(not r["d"] for r in it["rows"]):
            return it
    return next((it for it in sess["items"] if any(not r["d"] for r in it["rows"])), None)


def _set_feel(uid, widget_key):
    _item(st.session_state["sess"], uid)["feel"] = FEEL_KEY.get(st.session_state.get(widget_key))


def _add_set(uid):
    rows = _item(st.session_state["sess"], uid)["rows"]
    rows.append({**rows[-1], "d": False})


def _done_set(uid, i):
    sess = st.session_state["sess"]
    item, sid, unit = _item(sess, uid), sess["id"], sess["unit"]
    row = item["rows"][i]
    row["w"] = float(st.session_state.get(f"{sid}:{uid}:{i}:w", row["w"]))
    row["r"] = int(st.session_state.get(f"{sid}:{uid}:{i}:r", row["r"]))
    row["d"] = True
    if _is_hold(item):  # a hold's record is time: your longest, once there's one to beat
        best = _best_hold(item)
        earlier = max([int(r["r"]) for n, r in enumerate(item["rows"]) if r["d"] and n != i] or [0])
        if best and row["r"] > max(best, earlier):
            st.toast(f"New best on {item['exercise']}: :violet[**{amount(0, row['r'], unit, 'hold')}**]",
                     icon=":material/emoji_events:")
    else:
        tracker = training.PRTracker(item["prev"], item["lift"].get("pr_weight"), item["lift"].get("pr_reps"))
        kind = None
        for r in item["rows"]:
            if r["d"] and r["r"] > 0:
                kind = tracker.add(training.from_unit(r["w"], unit), int(r["r"]))
        if kind:
            w = training.from_unit(row["w"], unit)
            what = "heaviest ever" if kind == "weight" else "most reps ever" if not w else "most reps at this weight"
            st.toast(f"New PR on {item['exercise']}: :violet[**{amount(w, row['r'], unit)}**] ({what})",
                     icon=":material/emoji_events:")
    for r in item["rows"]:
        if not r["d"]:
            r["w"] = row["w"]  # the next set starts from the weight you just used
    sess["rest"] = {"until": time.time() + rest_seconds(item["exercise"]), "uid": uid, "total": rest_seconds(item["exercise"])}
    import gifs
    gifs.new_round("rest")
    sess["last_done"] = {"uid": uid, "i": i}
    session_data.save_live(st.session_state["username"], sess)  # kept even if the phone sleeps or the page reloads


def _skip_rest():
    st.session_state["sess"].pop("rest", None)


def _add_rest(secs):
    rest = st.session_state["sess"].get("rest")
    if rest:
        rest["until"] = max(time.time() + 5, rest["until"] + secs)
        rest["total"] = max(5, int(rest.get("total") or 60) + secs)


def _to_end(uid):
    sess = st.session_state["sess"]
    sess["items"].append(sess["items"].pop(next(n for n, x in enumerate(sess["items"]) if x["uid"] == uid)))
    sess.pop("focus", None)
    sess.pop("rest", None)


def _focus(uid):
    sess = st.session_state["sess"]
    sess["focus"] = uid
    sess.pop("rest", None)


def _discard():
    st.session_state.pop("sess", None)
    session_data.clear_live(st.session_state["username"])
    _go("landing")


def _done_rows(item, unit):
    return [
        {"weight": training.from_unit(r["w"], unit), "reps": int(r["r"]), "row": r}
        for r in item["rows"] if r["d"] and r["r"] > 0
    ]


@st.dialog("Discard this workout?")
def _confirm_discard():
    st.write("Nothing from this workout will be saved.")
    if st.button("Yes, discard it", type="primary", key="t_discard_yes", width="stretch"):
        _discard()
        st.rerun()
    if st.button("Keep going", key="t_discard_no", width="stretch"):
        st.rerun()


@st.fragment(run_every=1)
def _rest_panel():
    sess = st.session_state.get("sess")
    rest = sess.get("rest") if sess else None
    if not rest:
        return
    left = int(rest["until"] - time.time())
    if left <= 0:
        sess.pop("rest", None)
        ui.ping()  # rest is over: a chime, so people can look away while resting
        st.rerun()
    item = _item(sess, rest["uid"])
    remaining = sum(1 for r in item["rows"] if not r["d"])
    nxt = "Breathe. Your next set is below." if remaining else "Exercise done. Next one is below."
    total = max(left, int(rest.get("total") or rest_seconds(item["exercise"])))
    pct = 100 * left / total if total else 0
    # the ring drains smoothly: a CSS animation from where it is now to empty, over the seconds left
    # (the CSS escapes \\3c and \\3e write < and >: a literal "<number>" looks like a tag and the style is dropped)
    st.html("<style>@property --p{syntax:'\\3c number\\3e';inherits:false;initial-value:0}"
            "@keyframes bsDrain{to{--p:0}}.bs-ring{width:min(62vw,230px);aspect-ratio:1;border-radius:50%;margin:1rem auto .4rem;display:grid;"
            "place-items:center;background:conic-gradient(var(--bs-accent-ink) calc(var(--p)*1%),var(--bs-accent-soft) 0);"
            "animation:bsDrain var(--left) linear forwards}.bs-ring>div{width:86%;aspect-ratio:1;border-radius:50%;background:var(--bs-page-bg);"
            "display:grid;place-items:center;text-align:center}.bs-ring .n{font-size:3.4rem;font-weight:750;letter-spacing:-.03em;"
            "font-variant-numeric:tabular-nums;line-height:1}.bs-ring .l{opacity:.65;font-size:.85rem;margin-top:.3rem}"
            ".bs-rest-l{text-align:center;opacity:.75;margin-bottom:.6rem}</style>"
            f"<div class='bs-ring' style='--p:{pct:.1f};--left:{max(left, 1)}s' role='timer' aria-label='{left} seconds of rest left'><div><div>"
            f"<div class='n'>{left // 60}:{left % 60:02d}</div><div class='l'>Rest</div></div></div></div>"
            f"<div class='bs-rest-l'>{nxt}</div>")
    import gifs
    gifs.show(st.session_state["username"], "rest", height=130)  # encouragement, and a G-rated GIF if switched on
    with st.container(key="bs-rest3"):
        c = st.columns(3)
        c[0].button("-15 s", key="t_rest_m", on_click=_add_rest, args=(-15,), width="stretch")
        c[1].button("+15 s", key="t_rest_p", on_click=_add_rest, args=(15,), width="stretch")
        if c[2].button("Skip rest", key="t_rest_s", type="primary", width="stretch"):
            _skip_rest()
            st.rerun()
    secs = rest_seconds(item["exercise"])
    why = "" if secs <= 15 else research.why("rest-strength" if secs >= 150 else "rest-hypertrophy")
    if why:
        st.caption("Why this long? " + why)
    elif secs <= 15:
        st.caption("A short pause to change position.")


SESSION_CSS = """
<style>
/* Live workout (focus mode): least decoration, biggest numbers, one next action pinned to the bottom. */
.bs-seg { display: flex; gap: 5px; margin: .2rem 0 .9rem; }
.bs-seg i { flex: 1; height: 5px; border-radius: 99px; background: rgba(139,92,246,.18); }
.bs-seg i.done { background: rgba(139,92,246,.55); }
.bs-seg i.now { background: var(--bs-grad); }
.bs-ex-h { font-size: 1.6rem; font-weight: 700; letter-spacing: -.02em; line-height: 1.15; margin: 0 0 .35rem; }
.bs-ex-sub { opacity: .75; margin: 0 0 .2rem; font-size: .95rem; }
.bs-ex-sub b { opacity: 1; }
.bs-sets { width: 100%; border-collapse: collapse; margin: .6rem 0 .4rem; font-variant-numeric: tabular-nums; }
.bs-sets th { font-size: .68rem; letter-spacing: .08em; text-transform: uppercase; opacity: .55; font-weight: 600; text-align: left; padding: 0 .4rem .35rem; }
.bs-sets td { padding: .55rem .4rem; border-top: 1px solid rgba(139,92,246,.16); font-size: .98rem; }
.bs-sets td.c, .bs-sets th.c { text-align: center; }
.bs-sets tr.up td { color: color-mix(in srgb, currentColor 55%, transparent); }
.bs-sets tr.now td { background: rgba(139,92,246,.10); font-weight: 650; }
.bs-sets tr.now td:first-child { border-radius: 10px 0 0 10px; } .bs-sets tr.now td:last-child { border-radius: 0 10px 10px 0; }
.bs-sets .tick { font-family: 'Material Symbols Rounded'; font-size: 20px; color: #7c3aed; font-weight: normal; }
.bs-sets .prev span { opacity: .6; font-weight: 500; }
.st-key-bs-pair [data-testid="stHorizontalBlock"], .st-key-bs-big [data-testid="stHorizontalBlock"], .st-key-bs-rest3 [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .6rem; }
.st-key-bs-pair [data-testid="stColumn"], .st-key-bs-big [data-testid="stColumn"], .st-key-bs-rest3 [data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }
.st-key-bs-big label p { font-size: .78rem !important; letter-spacing: .06em; text-transform: uppercase; opacity: .65; font-weight: 600; }
.st-key-bs-big input { font-size: 1.9rem !important; font-weight: 700 !important; height: 64px; min-height: 64px !important; text-align: center; letter-spacing: -.02em; }
.st-key-bs-big [data-testid="stNumberInputContainer"] { height: 64px !important; }
.st-key-bs-big [data-testid="stNumberInputContainer"] > div { height: 100%; align-items: center; }
.st-key-bs-big [data-testid="stNumberInputContainer"] button { width: 44px; height: 100% !important; min-height: 0 !important; }
[data-testid="stLayoutWrapper"]:has(> .st-key-bs-donebar) { position: sticky; bottom: 0; z-index: 5; }
.st-key-bs-donebar { padding: .7rem 0 .9rem; margin-top: .3rem; background: transparent; }
/* The pinned bar is see-through, so it must let taps through to what's under it (a day pill, a list row);
   only its own buttons and text catch taps. */
[data-testid="stLayoutWrapper"]:has(> .st-key-bs-donebar), .st-key-bs-donebar, .st-key-bs-donebar > div { pointer-events: none; }
.st-key-bs-donebar button, .st-key-bs-donebar [data-testid="stCaptionContainer"], .st-key-bs-donebar a { pointer-events: auto; }
@media (max-width: 1023px) {
  header[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none !important; }
  .block-container { padding-top: 1rem !important; }
}
@media (max-width: 767px) {
  [data-testid="stImage"] img { max-height: 190px !important; object-fit: contain !important; border-radius: 16px; }
}
.st-key-bs-donebar button[kind="primary"] { height: 56px; border-radius: 999px !important; font-size: 1.05rem; }
.st-key-keep-sess-top [data-testid="stHorizontalBlock"] { justify-content: space-between; }
.st-key-keep-sess-top [data-testid="stCaptionContainer"] { text-align: right; }
.st-key-keep-sess-top [data-testid="stColumn"]:nth-child(3) { flex: 0 0 auto !important; }
.st-key-keep-sess-top [data-testid="stColumn"]:nth-child(3) button span[data-testid="stIconMaterial"] { font-size: 30px; color: var(--bs-accent-ink); }
.bs-next { display: flex; align-items: center; gap: .9rem; padding: .8rem 0; border-top: 1px solid rgba(139,92,246,.16); border-bottom: 1px solid rgba(139,92,246,.16); margin: .4rem 0 .6rem; }
.bs-next img { width: 56px; height: 56px; border-radius: 12px; object-fit: cover; }
.bs-next .k { font-size: .7rem; letter-spacing: .12em; text-transform: uppercase; opacity: .6; font-weight: 600; }
.bs-next .t { font-weight: 650; }
.bs-next .d { opacity: .7; font-size: .9rem; }
</style>
"""


def _num(v):
    return f"{float(v):g}"


def _prev_session(item):
    """The sets from the last time you did this exercise, in order (for the PREVIOUS column)."""
    prev = item["prev"]
    if not prev:
        return []
    last = prev[-1]["session_id"]
    return sorted((p for p in prev if p["session_id"] == last), key=lambda p: p["set_no"])


def _set_table(item, unit, now_i, bw):
    """Every set of this exercise on one table: done (ticked), now (highlighted), still to do (faded)."""
    prev = _prev_session(item)
    hold = _is_hold(item)
    head = ('<tr><th>Set</th><th>Previous</th>' + ("" if bw else f'<th class="c">{unit}</th>')
            + f'<th class="c">{"Sec" if hold else "Reps"}</th><th class="c"></th></tr>')
    body = []
    for n, r in enumerate(item["rows"]):
        p = prev[n] if n < len(prev) else None
        ptxt = ("" if p is None else (f"{p['reps']} s" if hold else f"{p['reps']} reps" if bw else f"{_num(round(training.to_unit(p['weight'], unit), 1))} × {p['reps']}")) or "&ndash;"
        cls = "done" if r["d"] else "now" if n == now_i else "up"
        mark = '<span class="tick">check_circle</span>' if r["d"] else ""
        body.append(f'<tr class="{cls}"><td>{n + 1}</td><td class="prev"><span>{ptxt}</span></td>'
                    + ("" if bw else f'<td class="c">{_num(r["w"])}</td>') + f'<td class="c">{int(r["r"])}</td><td class="c">{mark}</td></tr>')
    st.html(f'<table class="bs-sets" aria-label="Sets for {html.escape(item["exercise"])}">{head}{"".join(body)}</table>')


NOW_CSS = """<style>
/* The set screen: the move fills the screen, the name sits in the middle, controls stay out of the way. */
.st-key-bs-stage { display: flex; justify-content: center; align-items: center; }
.st-key-bs-stage [data-testid="stElementContainer"] { width: auto !important; margin: 0 auto; }
.st-key-bs-stage [data-testid="stImage"] img { max-height: min(46vh, 420px) !important; width: auto !important; max-width: 100%;
  object-fit: contain !important; border-radius: 22px; margin: 0 auto; display: block; }
.st-key-bs-stage [data-testid="stImage"] { display: flex; justify-content: center; width: 100%; }
.bs-demo { display: flex; justify-content: center; }
.bs-demo img { max-height: min(46vh, 420px); width: auto; max-width: 100%; object-fit: contain; border-radius: 22px; display: block; }
.bs-now { text-align: center; margin: .8rem 0 .2rem; }
.bs-now .nm { font-size: clamp(1.6rem, 6vw, 2.1rem); font-weight: 700; letter-spacing: -.02em; line-height: 1.12; }
.bs-now .st { opacity: .7; margin-top: .25rem; }
.bs-now .wk { margin-top: .2rem; font-size: .9rem; font-weight: 600; color: var(--bs-accent-ink); }
.bs-clock { text-align: center; font-variant-numeric: tabular-nums; font-size: clamp(3.4rem, 15vw, 4.6rem); font-weight: 750;
  letter-spacing: -.03em; line-height: 1; margin: .6rem 0 .2rem; }
.bs-clock.done { background: var(--bs-grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
.bs-clock-l { text-align: center; opacity: .65; font-size: .9rem; margin-bottom: .4rem; }
.st-key-bs-holdbtn { display: flex; align-items: center; }
.st-key-bs-holdbtn > div, .st-key-bs-holdbtn [data-testid="stElementContainer"] { width: 100% !important; display: flex; justify-content: center; }
.st-key-bs-holdbtn .stButton { max-width: none !important; width: auto !important; margin: 0 auto; }
.st-key-bs-holdbtn button { width: 64px !important; height: 64px; border-radius: 50% !important; padding: 0 !important;
  background: var(--bs-accent-soft) !important; border: none !important; }
.st-key-bs-holdbtn button span[data-testid="stIconMaterial"] { font-size: 34px; color: var(--bs-accent-ink) !important; margin: 0 !important; }
.st-key-keep-bs-corner [data-testid="stHorizontalBlock"] { justify-content: space-between; }
.st-key-keep-bs-corner [data-testid="stColumn"] { flex: 0 0 auto !important; }
.bs-elapsed { text-align: center; font-variant-numeric: tabular-nums; font-weight: 650; }
.bs-elapsed small { display: block; font-size: .7rem; opacity: .6; font-weight: 500; }
</style>"""


def _workout_seconds(sess):
    """Time spent training: since Start workout, minus any time paused."""
    try:
        secs = (datetime.now() - datetime.fromisoformat(sess["started"])).total_seconds()
    except (KeyError, ValueError, TypeError):
        return 0
    paused = sess.get("paused_total", 0) + (time.time() - sess["paused_at"] if sess.get("paused_at") else 0)
    return max(0, int(secs - paused))


def _pause(sess):
    sess["paused_at"] = time.time()
    session_data.save_live(st.session_state["username"], sess)


def _resume(sess):
    gap = time.time() - sess.pop("paused_at", time.time())
    sess["paused_total"] = sess.get("paused_total", 0) + gap
    if sess.get("rest"):  # a rest that was running carries on from where it was
        sess["rest"]["until"] += gap
    session_data.save_live(st.session_state["username"], sess)


PAUSE_CSS = """<style>
.bs-paused { text-align: center; margin: 1.6rem 0 .6rem; }
.bs-paused .k { font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--bs-accent-ink); }
.bs-paused .n { font-size: clamp(3rem, 14vw, 4.2rem); font-weight: 800; letter-spacing: -.03em; font-variant-numeric: tabular-nums; line-height: 1.05; }
.bs-paused .d { opacity: .7; margin-top: .2rem; }
.st-key-bs-resume { display: flex; justify-content: center; margin: 1.2rem 0 1.4rem; }
.st-key-bs-resume [data-testid="stElementContainer"], .st-key-bs-resume .stButton { width: 100% !important;
  max-width: none !important; display: flex !important; justify-content: center; }
.st-key-bs-resume button { width: 132px !important; height: 132px; border-radius: 50% !important; padding: 0 !important;
  background: var(--bs-grad) !important; border: none !important; box-shadow: 0 10px 30px rgba(124,58,237,.35); }
.st-key-bs-resume button span[data-testid="stIconMaterial"] { font-size: 64px; color: #fff !important; margin: 0 !important; }
.st-key-bs-resume button p { display: none; }
</style>"""


@st.fragment(run_every=1)
def _paused_clock(sess):
    gap = int(time.time() - (sess.get("paused_at") or time.time()))
    st.html(f'<div class="bs-paused"><div class="k">Paused</div><div class="n">{gap // 60}:{gap % 60:02d}</div>'
            '<div class="d">Your workout clock and rest are on hold.</div></div>')


def _paused_view(username, sess, cur, done, total):
    """While paused: how long it's been, one big round Resume, what comes next, and the quieter options."""
    st.html(PAUSE_CSS)
    _paused_clock(sess)
    with st.container(key="bs-resume"):
        st.button("Resume", icon=":material/play_arrow:", key=f"{sess['id']}:resume", on_click=_resume, args=(sess,),
                  help="Resume the workout")
    st.html(f'<p style="text-align:center;font-weight:650;margin:0 0 1rem">Tap to resume  ·  {done} of {total} sets done</p>')
    if cur:
        _up_next(sess, cur)
    with st.container(key="keep-pause-more"):
        a, b = st.columns(2)
        if a.button("Edit plan", icon=":material/tune:", key=f"{sess['id']}:pplan", width="stretch"):
            _resume(sess)
            _open_editor(sess)
            st.rerun()
        if b.button("End workout", icon=":material/flag:", key=f"{sess['id']}:pend", width="stretch"):
            _resume(sess)
            _end_dialog(username, done)


@st.fragment(run_every=1)
def _elapsed_clock():
    sess = st.session_state.get("sess")
    if not sess:
        return
    secs = _workout_seconds(sess)
    h, m = divmod(secs // 60, 60)
    st.html(f'<div class="bs-elapsed">{f"{h}:" if h else ""}{m:02d}:{secs % 60:02d}<small>workout time</small></div>')


@st.fragment(run_every=1)
def _hold_clock(key, target, value_key):
    """A countdown for a hold: start, pause, and a chime at zero. The seconds logged follow the clock."""
    t = st.session_state.setdefault(key, {"acc": 0.0, "t0": None, "rang": False})
    held = t["acc"] + (time.time() - t["t0"] if t["t0"] else 0)
    left = max(0, int(round(target - held)))
    if left == 0 and not t["rang"]:
        t.update(rang=True, acc=float(target), t0=None)
        st.session_state[value_key] = int(target)
        ui.ping()
        st.rerun(scope="app")
    st.html(f'<div class="bs-clock {"done" if left == 0 else ""}">{left // 60}:{left % 60:02d}</div>'
            f'<div class="bs-clock-l">{"Held. Tap Done." if left == 0 else "Holding" if t["t0"] else "Tap play when you are in position"}</div>')
    with st.container(key="bs-holdbtn"):
        if t["t0"]:
            if st.button("", icon=":material/pause:", key=f"{key}:pause", help="Pause"):
                t["acc"] += time.time() - t["t0"]
                t["t0"] = None
                st.session_state[value_key] = int(t["acc"])
                st.rerun()
        elif left > 0 and st.button("", icon=":material/play_arrow:", key=f"{key}:go", help="Start the hold"):
            t["t0"] = time.time()
            st.rerun()


# Warm-ups (moving, about 5 minutes) and cool-downs (gentle holds), picked for the day's body area.
WARMUPS = {"upper": ["Arm Circles", "Shoulder Circles", "Dynamic Chest Stretch", "Inchworm"],
           "lower": ["Standing Hip Circles", "Front Leg Raises", "Side Leg Raises", "Bodyweight Squat"],
           "full": ["Arm Circles", "Standing Hip Circles", "Inchworm", "Bodyweight Squat"]}
COOLDOWNS = {"upper": ["Child's Pose", "Shoulder Stretch", "Triceps Stretch", "Seated Biceps"],
             "lower": ["Kneeling Hip Flexor", "Seated Floor Hamstring Stretch", "Lying Glute", "Standing Gastrocnemius Calf Stretch"],
             "full": ["Child's Pose", "Kneeling Hip Flexor", "Seated Floor Hamstring Stretch", "Shoulder Stretch"]}


def _area(sess):
    """Which warm-up fits: the day type, else guessed from what's in the workout."""
    if sess["day"] in ("upper", "lower", "full"):
        return sess["day"]
    kinds = {x["lift"].get("day_type") for x in sess["items"] if not x["lift"].get("phase")}
    return "upper" if kinds <= {"upper", "core"} else "lower" if kinds <= {"lower"} else "full"


def _add_phase(sess, phase):
    """Insert the warm-up (at the start) or cool-down (at the end). Logged as stretching, never as lifts."""
    username = st.session_state["username"]
    names = (WARMUPS if phase == "warmup" else COOLDOWNS)[_area(sess)]
    names = [n for n in names if n not in {x["exercise"] for x in sess["items"]}] or names
    tpl = {n: {"sets": 1, "rep_low": 10 if phase == "warmup" else 30, "rep_high": 10 if phase == "warmup" else 30,
               "hold": phase == "cooldown", "phase": phase} for n in names}
    st.session_state["t_template"] = tpl
    planned = _plan(username, names)
    st.session_state.pop("t_template", None)
    unit = sess["unit"]
    new = []
    for lift, sug in planned:
        target = int(lift.get("rep_low") or 10)
        sug = {**sug, "weight": None, "reps": target, "sets": 1, "tag": "repeat",
               "reason": ("Easy and moving: just enough to feel warm. Then do 1 or 2 light sets of your first lift."
                          if phase == "warmup" else "Breathe out and ease in. Mild tension, never pain.")}
        new.append({"uid": uuid.uuid4().hex[:8], "exercise": lift["exercise"], "lift": lift, "sug": sug,
                    "step": float(training.step(lift["day_type"], unit)), "prev": [],
                    "rows": [{"w": 0.0, "r": target, "d": False}]})
    if phase == "warmup":
        sess["items"] = new + sess["items"]
        sess["focus"] = new[0]["uid"]
    else:
        sess["items"] = sess["items"] + new
        sess["focus"] = new[0]["uid"]
    sess[f"{phase}_asked"] = True
    session_data.save_live(username, sess)


def _phase_offer(sess, phase, minis_for):
    """A small card: warm up first / cool down now. Add or skip; nothing is forced."""
    names = (WARMUPS if phase == "warmup" else COOLDOWNS)[_area(sess)]
    minis = prepare_minis([e for e in (find_exercise(n) for n in names) if e])
    imgs = "".join(f'<img src="{html.escape(minis[n])}" alt="">' for n in names if minis.get(n))
    title = "Warm up first" if phase == "warmup" else "Cool down"
    why = research.get("warmup-stretch" if phase == "warmup" else "cooldown") or {}
    st.html("<style>.bs-phase{border-radius:18px;padding:.9rem 1rem;background:var(--bs-accent-soft);margin:.2rem 0 .6rem}"
            ".bs-phase .im{display:flex;gap:6px;margin:.5rem 0}.bs-phase .im img{width:52px;height:52px;border-radius:12px;"
            "object-fit:cover}.bs-phase .t{font-weight:650}.bs-phase .d{font-size:.85rem;opacity:.75}</style>"
            f'<div class="bs-phase"><div class="t">{title} · about 5 min</div><div class="im">{imgs}</div>'
            f'<div class="d">{html.escape(", ".join(names))}</div></div>')
    with st.container(key=f"keep-phase-{phase}"):
        a, b = st.columns(2)
        if a.button("Add warm-up" if phase == "warmup" else "Add cool-down", type="primary", key=f"{sess['id']}:{phase}:add",
                    width="stretch", icon=":material/add:"):
            _add_phase(sess, phase)
            st.rerun()
        if b.button("Skip" if phase == "warmup" else "Finish now", key=f"{sess['id']}:{phase}:skip", width="stretch"):
            sess[f"{phase}_asked"] = True
            if phase == "cooldown":
                st.session_state["t_finish_now"] = True
            st.rerun()
    if why.get("source"):
        st.caption(f"{why['claim']} ([source]({why['source']}))")


def start_stretch(username, pages, area="full"):
    """A 5-minute stretch you can start any time (rest days, or after training): the cool-down holds."""
    names = COOLDOWNS.get(area, COOLDOWNS["full"])
    w = {"id": "rest-stretch", "title": "5-minute stretch", "focus": "stretch", "level": "Beginner", "equipment": "None",
         "exercises": [[n, 1, 30, 30, "hold"] for n in names]}
    _start_template(username, w)
    st.session_state["t_go_session"] = True
    ui.to_workout(pages)


def _swap_item(sess, uid, new_name):
    """Replace an exercise in today's workout with another for the same muscles. Sets you already did are kept."""
    username = st.session_state["username"]
    old = _item(sess, uid)
    done = [r for r in old["rows"] if r["d"]]
    lift_base = {k: old["lift"].get(k) for k in ("sets", "rep_low", "rep_high") if old["lift"].get(k)}
    st.session_state["t_template"] = {new_name: {**lift_base, "hold": bool(old["lift"].get("hold"))}}
    lift, sug = _plan(username, [new_name])[0]
    st.session_state.pop("t_template", None)
    if lift.get("hold"):
        sug = {**sug, "weight": None, "reps": int(old["sug"]["reps"]), "tag": "repeat", "reason": old["sug"]["reason"]}
    unit = sess["unit"]
    w = float(round(training.to_unit(sug["weight"], unit), 1)) if sug["weight"] else 0.0
    left = max(1, len(old["rows"]) - len(done))
    new = {"uid": uuid.uuid4().hex[:8], "exercise": new_name, "lift": lift, "sug": sug,
           "step": float(training.step(lift["day_type"], unit)),
           "prev": [x for x in session_data.all_sets(username) if x["exercise"] == new_name],
           "rows": [{"w": w, "r": sug["reps"], "d": False} for _ in range(left)]}
    i = next(n for n, x in enumerate(sess["items"]) if x["uid"] == uid)
    if done:  # keep what you did on the old one, and put the swap right after it
        old["rows"] = done
        sess["items"].insert(i + 1, new)
    else:
        sess["items"][i] = new
    sess["focus"] = new["uid"]
    session_data.save_live(username, sess)


@st.dialog("Options")
def _options_dialog(sess, uid):
    """Changes to the plan live here, out of the way of the set itself."""
    item = _item(sess, uid)
    name = item["exercise"]
    hold = _is_hold(item)
    st.markdown(f"**{name}**")
    done_n = sum(1 for r in item["rows"] if r["d"])
    a, b = st.columns(2)
    n_sets = a.number_input("Sets", max(1, done_n), 10, len(item["rows"]), key=f"opt_sets_{uid}")
    target = (b.number_input("Hold (seconds)", 5, 600, int(item["sug"]["reps"]), 5, key=f"opt_t_{uid}") if hold
              else b.number_input("Reps to aim for", 1, 100, int(item["sug"]["reps"]), key=f"opt_t_{uid}"))
    remember = st.toggle("Remember for next time", value=True, key=f"opt_mem_{uid}",
                         help="Every future workout with this exercise starts with these numbers.")
    if st.button("Save changes", type="primary", icon=":material/check:", key=f"opt_save_{uid}", width="stretch"):
        rows = item["rows"]
        while len(rows) < n_sets:
            rows.append({**rows[-1], "d": False})
        while len(rows) > n_sets and not rows[-1]["d"]:
            rows.pop()
        item["sug"] = {**item["sug"], "reps": int(target), "sets": int(n_sets)}
        for r in rows:
            if not r["d"]:
                r["r"] = int(target)
        for k in [k for k in st.session_state if k.startswith(f"{sess['id']}:{uid}:")]:
            del st.session_state[k]  # the set screen picks up the new numbers
        if remember:
            username = st.session_state["username"]
            prefs = dict(session_data.settings(username).get("ex_prefs") or {})
            prefs[name] = {"sets": int(n_sets), **({"target": int(target)} if hold else {})}
            session_data.save_settings(username, ex_prefs=prefs)
        session_data.save_live(st.session_state["username"], sess)
        st.toast("Saved. Next time starts with these numbers." if remember else "Changed for today",
                 icon=":material/check_circle:")
        st.rerun()
    st.divider()
    if len([x for x in sess["items"] if any(not r["d"] for r in x["rows"])]) > 1:
        if st.button("Do it later", icon=":material/skip_next:", key=f"opt_later_{uid}", width="stretch",
                     help="Moves it to the end of today's list. It is not discarded."):
            _to_end(uid)
            st.rerun()
    alts = training.alternatives(name, load_exercises(), 3, avoid={x["exercise"] for x in sess["items"]}, hold=hold)
    if alts:
        st.markdown("**Swap for a similar exercise**")
        st.caption("Same main muscles. Sets you already did stay logged.")
        minis = prepare_minis([e for e in (find_exercise(a) for a in alts) if e])
        for n_, alt in enumerate(alts):
            ex = find_exercise(alt) or {}
            with st.container(key=f"keep-swap-{uid}-{n_}"):
                pic, text, act = st.columns([1, 4, 2], vertical_alignment="center")
                if minis.get(alt):
                    with pic:
                        ui.thumb(minis[alt], "sm")
                text.markdown(f"**{alt}**")
                text.caption(", ".join(m.capitalize() for m in (ex.get("primaryMuscles") or [])) + "  ·  "
                             + (ex.get("equipment") or "no equipment").replace("body only", "no equipment").capitalize())
                if act.button("Swap", key=f"opt_swap_{uid}_{n_}", width="stretch"):
                    _swap_item(sess, uid, alt)
                    st.toast(f"Swapped to {alt}", icon=":material/swap_horiz:")
                    st.rerun()
        st.divider()
    if st.button("Change today's plan", icon=":material/tune:", key=f"opt_lineup_{uid}", width="stretch"):
        _open_editor(sess)
        st.rerun()
    if st.button("Close", key=f"opt_close_{uid}", width="stretch", type="tertiary"):
        st.rerun()


def _set_panel(sess, item):
    sid, unit, uid = sess["id"], sess["unit"], item["uid"]
    sug, name = item["sug"], item["exercise"]
    i = next(n for n, r in enumerate(item["rows"]) if not r["d"])
    row = item["rows"][i]
    hold = _is_hold(item)
    bw = is_bodyweight(name) or hold or _no_weight(item)
    st.html(NOW_CSS)

    ex = find_exercise(_media_name(item))
    demo = anim_url(ex) if ex else None
    if demo:  # an <img>, not st.image: st.image re-encodes animated WebP and only the first frame was left
        st.html(f'<div class="bs-demo"><img src="{html.escape(demo)}" alt="{html.escape(name)} demo"></div>')
    note = formtips.motion_note(_media_name(item))
    if note:  # two photos can't show this motion: say so and show the steps right here
        st.caption(note)
        st.markdown("\n".join(f"{n}. {t}" for n, t in enumerate(formtips.steps(_media_name(item)), 1)))
    side = " each side" if hold and (_per_side(name) or item["lift"].get("per_side")) else ""
    aim = (f"{sug['reps']} second hold{side}" if hold
           else f"{sug['reps']}+ reps" + ("" if bw or not row["w"] else f" at {training.fmt_weight(training.from_unit(row['w'], unit), unit)}"))
    target = targets.move(_media_name(item)) or targets.move(name)
    st.html(f'<div class="bs-now"><div class="nm">{html.escape(name)}</div>'
            f'<div class="st">Set {i + 1} of {len(item["rows"])}  ·  {html.escape(aim)}</div>'
            + (f'<div class="wk">Works: {html.escape(target["area"])}</div>' if target else "") + '</div>')

    value_key = f"{sid}:{uid}:{i}:r"
    if hold:
        st.session_state.setdefault(value_key, int(row["r"]))
        _hold_clock(f"{sid}:{uid}:{i}:clock", int(sug["reps"]), value_key)
    if not hold:  # a hold is logged by its clock; reps (and weight) are typed
        with st.container(key="bs-big"):
            c = st.columns(2 if not bw else 1)
            if not bw:
                c[0].number_input(f"Weight ({unit})", 0.0, 2000.0, float(row["w"]), float(item.get("step") or 5.0), format="%g", key=f"{sid}:{uid}:{i}:w")
            c[-1].number_input("Reps", 0, 100, int(row["r"]), 1, key=value_key)
    with st.container(key="keep-bs-corner"):
        a, b = st.columns(2)
        with a:
            formtips.render(name, f"{sid}{uid}")
        if b.button("Options", icon=":material/more_horiz:", key=f"{sid}:{uid}:opts", type="tertiary"):
            _options_dialog(sess, uid)
    ready = bw or float(st.session_state.get(f"{sid}:{uid}:{i}:w", row["w"])) > 0
    with st.container(key="bs-donebar"):
        st.button(f"Done with set {i + 1}", type="primary", width="stretch", icon=":material/check:", key=f"{sid}:{uid}:{i}:done",
                  on_click=_done_set, args=(uid, i), disabled=not ready)
        if not ready:
            st.caption("Pick a weight above zero to log this set.")

    # below the fold: the coaching notes and every set of this exercise
    if not item["prev"] and not bw:
        st.caption(f"First time. Pick a weight you could lift for {sug['reps']} reps with 2 or 3 left in the tank.")
    else:
        st.caption(("" if hold else TAG_TEXT[sug["tag"]] + ". ") + sug["reason"])
    if target:  # why this move is in the workout, under the coaching note
        e = research.get(target.get("research") or "") or {}
        link = f" ([source]({e['source']}))" if e.get("source") and e.get("status") == "verified" else ""
        st.caption(f"Why this move: {target['job']}{link}")
    care = easy_on(name, session_data.settings(st.session_state["username"]).get("injury_areas") or [])
    if care:
        st.caption(f"You asked to go easy on your {care}. Keep the range comfortable, and skip it or swap it "
                   "(Options) if it hurts.")
    _set_table(item, unit, i, bw)


def _plan_list(sess, cur):
    unit = sess["unit"]
    st.markdown("##### Today's plan")
    exercises = [find_exercise(_media_name(x)) for x in sess["items"]]
    minis = prepare_minis([e for e in exercises if e])
    for it in sess["items"]:
        n_done, n = sum(1 for r in it["rows"] if r["d"]), len(it["rows"])
        state = "Done" if n_done == n else "Now" if cur and it["uid"] == cur["uid"] else f"{n_done}/{n} sets"
        with st.container(key=f"keep-plan-{it['uid']}"):
            pic, text, act = st.columns([1, 5, 2])
            if minis.get(_media_name(it)):
                with pic:
                    ui.thumb(minis[_media_name(it)], "sm")
            text.markdown(f"**{it['exercise']}**")
            text.caption(f"{state}  ·  {len(it['rows'])} × {int(it['rows'][0]['r'])}" + (" s" if _is_hold(it) else "")
                         + ("" if is_bodyweight(it["exercise"]) or _no_weight(it) or not it['rows'][0]['w'] else f" @ {training.fmt_weight(training.from_unit(it['rows'][0]['w'], unit), unit)}"))
            if n_done < n and not (cur and it["uid"] == cur["uid"]):
                act.button("Do now", key=f"t_focus_{it['uid']}", on_click=_focus, args=(it["uid"],), width="stretch")


@st.dialog("End this workout?")
def _end_dialog(username, done):
    if done:
        st.write(f"You've logged {done} set{'s' if done != 1 else ''}. Finish to save them, or keep going.")
        if st.button("Finish and save", type="primary", key="t_end_finish", width="stretch"):
            st.session_state["t_finish_now"] = True
            st.rerun()
    else:
        st.write("Nothing is logged yet, so there's nothing to save.")
    if st.button("Keep going", key="t_end_keep", width="stretch"):
        st.rerun()
    if st.button("Discard workout", type="tertiary", icon=":material/delete:", key="t_end_discard", width="stretch"):
        _discard()
        st.rerun()


def _up_next(sess, cur):
    """While resting: the very next set, with its picture, so there is never a 'what now?' moment."""
    unit = sess["unit"]
    i = next(n for n, r in enumerate(cur["rows"]) if not r["d"])
    row = cur["rows"][i]
    ex = find_exercise(_media_name(cur))
    img = mini_url(ex) if ex else None
    what = (f"{int(row['r'])} s hold" if _is_hold(cur) else f"{int(row['r'])} reps" if is_bodyweight(cur["exercise"]) or _no_weight(cur) else f"{training.fmt_weight(training.from_unit(row['w'], unit), unit)} × {int(row["r"])}")
    st.html('<div class="bs-next">' + (f'<img src="{img}" alt="">' if img else "")
            + f'<div><div class="k">Up next</div><div class="t">{html.escape(cur["exercise"])}</div>'
            f'<div class="d">Set {i + 1} of {len(cur["rows"])}  ·  {what}</div></div></div>')


PLAN_CSS = """<style>
div[class*='st-key-keep-plan-hd-'] div[data-testid='stHorizontalBlock'] > div[data-testid='stColumn']:nth-child(3){flex:1 1 auto !important}
div[class*='st-key-keep-plan-hd-'] div[data-testid='stHorizontalBlock'] > div[data-testid='stColumn']:not(:nth-child(3)){flex:0 0 auto !important;width:auto !important}
[class*='st-key-keep-plan-hd-'] button{min-height:38px;padding:0 .55rem}
[class*='st-key-bs-mv-'] { gap: 2px !important; }
[class*='st-key-bs-mv-'] button { min-height: 26px !important; height: 26px; width: 34px; padding: 0 !important; border: none !important;
  background: transparent !important; }
[class*='st-key-bs-mv-'] button:disabled { opacity: .25; }
.bs-pname{font-weight:650;line-height:1.25}.bs-pname small{display:block;font-weight:500;opacity:.7;font-size:.82rem}
.bs-ready-meta{opacity:.75;margin:-.3rem 0 .4rem}
</style>"""


def _session_minutes(sess):
    return _minutes([(x["exercise"], len(x["rows"])) for x in sess["items"]])


def _move(sess, i, d):
    j = i + d
    if 0 <= j < len(sess["items"]):
        sess["items"][i], sess["items"][j] = sess["items"][j], sess["items"][i]
        session_data.save_live(st.session_state["username"], sess)


def _remove(sess, uid):
    sess["items"] = [x for x in sess["items"] if x["uid"] != uid]
    session_data.save_live(st.session_state["username"], sess)


def _plan_editor(username, sess):
    """Today's plan, editable: sets, reps (or seconds) and weight for each move, move it up or down, remove it,
    or add more. Sets you already did stay as they are."""
    st.html(PLAN_CSS)
    unit = sess["unit"]
    items = sess["items"]
    minis = prepare_minis([e for e in (find_exercise(_media_name(x)) for x in items) if e])
    if not items:
        st.caption("Nothing in today's plan yet. Add an exercise to start.")
    for i, it in enumerate(items):
        uid = it["uid"]
        done_n = sum(1 for r in it["rows"] if r["d"])
        hold, bw = _is_hold(it), is_bodyweight(it["exercise"]) or _no_weight(it)
        tag = "Warm-up" if it["lift"].get("phase") == "warmup" else "Cool-down" if it["lift"].get("phase") == "cooldown" else ""
        state = f"{done_n} of {len(it['rows'])} sets done" if done_n else tag
        with st.container(key=f"keep-plan-hd-{uid}"):  # reorder handle (stacked arrows) | picture | name | remove
            mv, pic, nm, sw, x = st.columns([1, 1, 5, 1, 1], vertical_alignment="center")
            with mv, st.container(key=f"bs-mv-{uid}"):
                st.button("", icon=":material/keyboard_arrow_up:", key=f"pe:{uid}:up", help="Move up", disabled=i == 0,
                          on_click=_move, args=(sess, i, -1))
                st.button("", icon=":material/keyboard_arrow_down:", key=f"pe:{uid}:dn", help="Move down",
                          disabled=i == len(items) - 1, on_click=_move, args=(sess, i, 1))
            with pic:
                ui.thumb(minis[_media_name(it)], "sm") if minis.get(_media_name(it)) else ui.icon_thumb("fitness_center")
            nm.html(f'<div class="bs-pname">{html.escape(it["exercise"])}' + (f"<small>{html.escape(state)}</small>" if state else "") + "</div>")
            if sw.button("", icon=":material/swap_horiz:", key=f"pe:{uid}:sw", help="Swap for a similar exercise"):
                import exercise_picker
                exercise_picker.swap_dialog(it["exercise"], hold, [x_["exercise"] for x_ in items],
                                            lambda new, u=uid: _swap_item(sess, u, new))
            x.button("", icon=":material/close:", key=f"pe:{uid}:rm", help="Remove" if not done_n else "Has logged sets",
                     disabled=bool(done_n), on_click=_remove, args=(sess, uid))
        open_rows = [r for r in it["rows"] if not r["d"]]
        first = open_rows[0] if open_rows else it["rows"][-1]
        with st.container(key=f"keep-plan-amt-{uid}"):
            cols = st.columns(2 if bw else 3)
            n = int(cols[0].number_input("Sets", max(1, done_n), 10, len(it["rows"]), key=f"pe:{uid}:n"))
            r = int(cols[1].number_input("Seconds" if hold else "Reps", 1, 600 if hold else 100, int(first["r"]),
                                         5 if hold else 1, key=f"pe:{uid}:r"))
            w = (float(cols[2].number_input(f"Weight ({unit})", 0.0, 2000.0, float(first["w"]), float(it.get("step") or 5.0),
                                            format="%g", key=f"pe:{uid}:w")) if not bw else 0.0)
        changed = n != len(it["rows"]) or any(row["r"] != r or (not bw and row["w"] != w) for row in open_rows)
        if changed:
            rows = it["rows"]
            while len(rows) < n:
                rows.append({"w": w, "r": r, "d": False})
            while len(rows) > n and not rows[-1]["d"]:
                rows.pop()
            for row in rows:
                if not row["d"]:
                    row["r"], row["w"] = r, (w if not bw else row["w"])
            it["sug"] = {**it["sug"], "reps": r, "sets": n}
            for k in [k for k in st.session_state if str(k).startswith(f"{sess['id']}:{uid}:")]:
                del st.session_state[k]  # the set screen picks up the new numbers
            session_data.save_live(username, sess)
        if i < len(items) - 1:
            st.divider()
    st.write("")
    if st.button("Add exercises", icon=":material/add:", key=f"pe:{sess['id']}:add"):
        _add_dialog(username, sess)


@st.dialog("Add exercises", width="large")
def _add_dialog(username, sess):
    """The same picker as New playlist. What's already in today's plan shows ticked."""
    import exercise_picker

    found, _ = exercise_picker.search(username, load_exercises(), "pa")
    have = {x["exercise"]: x for x in sess["items"]}
    shown = found[:25 * st.session_state.get("pa_page", 1)]
    minis = prepare_minis(shown)
    st.caption(f"{len(found)} exercises, A to Z. {len(have)} already in today's plan.")
    for e in shown:
        on = e["name"] in have
        locked = on and any(r["d"] for r in have[e["name"]]["rows"])
        opened, _ = ui.tap_row(f"pa-{e['id']}", minis.get(e["name"]), e["name"], exercise_picker.describe(e),
                               end="check_circle" if on else "add_circle", end_on=on)
        if opened and not locked:
            if on:
                _remove(sess, have[e["name"]]["uid"])
            else:
                sess["items"].extend(_make_items(username, [e["name"]]))
                session_data.save_live(username, sess)
            st.rerun(scope="fragment")
    if len(found) > len(shown) and st.button(f"Show more ({len(found) - len(shown)} left)", key="pa_more"):
        st.session_state["pa_page"] = st.session_state.get("pa_page", 1) + 1
        st.rerun(scope="fragment")
    if st.button("Done", type="primary", key="pa_done", width="stretch"):
        st.session_state.pop("pa_page", None)
        st.rerun()


def _open_editor(sess):
    sess["editing"] = True
    ui.to_top()
    for k in [k for k in st.session_state if str(k).startswith("pe:")]:
        del st.session_state[k]


def _cancel_ready(pages):
    back = (st.session_state.pop("sess", None) or {}).get("from")
    session_data.clear_live(st.session_state["username"])
    if back and pages and back in pages:
        st.switch_page(pages[back])
    _go("day")


def _ready_view(username, sess, pages):
    """Before the clock starts: the workout at a glance, a warm-up offer, and the plan you can still change."""
    import body_map

    if st.button("Back", icon=":material/arrow_back:", key=f"{sess['id']}:rback"):
        _cancel_ready(pages)
        st.rerun()
    main = [x for x in sess["items"] if not x["lift"].get("phase")]
    title = sess.get("source") or dict((k, l) for k, _, l in DAYS).get(sess["day"], "Your workout")
    st.title(title, anchor=False)
    n = len(sess["items"])
    st.html(f'<div class="bs-ready-meta">{n} move{"s" if n != 1 else ""}  ·  about {_session_minutes(sess)} min</div>')
    m, a = body_map.muscles_for([e for e in (find_exercise(_media_name(x)) for x in main) if e])
    if m:
        st.markdown(body_map.works_line(m, a))
    strength_day = sess["day"] not in ("stretch", "cardio") and main and not all(_is_hold(x) for x in main)
    if strength_day and not sess.get("warmup_asked"):
        _phase_offer(sess, "warmup", None)
    st.markdown("##### Today's plan")
    _plan_editor(username, sess)
    st.html(SESSION_CSS)
    with st.container(key="bs-donebar"):
        if st.button("Start workout", type="primary", icon=":material/play_arrow:", key=f"{sess['id']}:go",
                     width="stretch", disabled=not sess["items"]):
            sess.update(ready=False, warmup_asked=True, started=datetime.now().isoformat(timespec="seconds"))
            ui.to_top()
            session_data.save_live(username, sess)
            st.rerun()


def _edit_view(username, sess):
    """Change the plan in the middle of a workout, without starting over."""
    st.markdown("### Change today's plan")
    st.caption("Reorder, change numbers, remove or add. Sets you already did stay logged.")
    _plan_editor(username, sess)
    st.html(SESSION_CSS)
    with st.container(key="bs-donebar"):
        if st.button("Back to the workout", type="primary", icon=":material/check:", key=f"{sess['id']}:edone",
                     width="stretch"):
            sess.pop("editing", None)
            ui.to_top()
            session_data.save_live(username, sess)
            st.rerun()


def session_view(username, pages=None):
    st.session_state["_focus_mode"] = True  # no tab bar: the workout gets the whole screen, End is always at the top
    st.html(SESSION_CSS)
    st.html(NOW_CSS)  # the top bar clock and the set screen share these styles
    sess = st.session_state["sess"]
    for it in sess["items"]:
        it.setdefault("uid", uuid.uuid4().hex[:8])
    if sess.get("ready"):
        _ready_view(username, sess, pages)
        return
    unit = sess["unit"]
    items = sess["items"]
    total = sum(len(i["rows"]) for i in items)
    done = sum(len(_done_rows(i, unit)) for i in items)
    cur = _current(sess)

    paused = bool(sess.get("paused_at"))
    with st.container(key="keep-sess-top"):
        a, m, p, b = st.columns([1, 1.2, .5, .8], vertical_alignment="center")
        if a.button("End", icon=":material/close:", key=f"{sess['id']}:end", type="tertiary"):
            _end_dialog(username, done)
        with m:
            _elapsed_clock()
        if not paused:
            p.button("", icon=":material/pause_circle:", key=f"{sess['id']}:pause", type="tertiary",
                     on_click=_pause, args=(sess,), help="Pause the workout")
        b.html(f'<div style="text-align:right;font-variant-numeric:tabular-nums;font-weight:650">{done}/{total}'
               f'<small style="display:block;font-size:.7rem;opacity:.6;font-weight:500">sets</small></div>')
    segs = "".join(
        f'<i class="{"done" if all(r["d"] for r in it["rows"]) else "now" if cur and it["uid"] == cur["uid"] else ""}"></i>'
        for it in items)
    st.html(f'<div class="bs-seg" role="img" aria-label="{done} of {total} sets done">{segs}</div>')

    resting = sess.get("rest") and sess["rest"]["until"] > time.time()
    strength_day = sess["day"] not in ("stretch", "cardio") and not all(_is_hold(x) for x in items)
    offered = None
    if strength_day and done == 0 and not sess.get("warmup_asked") and not resting:
        offered = "warmup"
    elif strength_day and cur is None and not resting and not sess.get("cooldown_asked"):
        offered = "cooldown"
    if sess.get("editing"):
        _edit_view(username, sess)
        return
    if paused:  # one clear thing to do while paused: a big Resume, how long it's been, and what's next
        _paused_view(username, sess, cur, done, total)
        return
    if offered:  # one thing at a time: the offer takes the place of the set screen
        _phase_offer(sess, offered, None)
    elif resting:
        _rest_panel()
        if cur:
            _up_next(sess, cur)
    elif cur:
        _set_panel(sess, cur)
    else:
        st.success("Every set is done. Nice work. Finish to save it.", icon=":material/check_circle:")

    done_item = _item(sess, sess["last_done"]["uid"]) if sess.get("last_done") and any(
        x["uid"] == sess["last_done"]["uid"] for x in items) else None
    feel_item = done_item or cur
    main_lift = feel_item and not (feel_item["lift"].get("phase") or feel_item["lift"].get("skill_part"))
    if main_lift and not _is_hold(feel_item) and any(r["d"] for r in feel_item["rows"]) and (resting or not cur or cur["uid"] == feel_item["uid"]):
        fk = f"{sess['id']}:{feel_item['uid']}:feel"
        st.segmented_control(f"How did {feel_item['exercise']} feel?", formtips.FEELS, key=fk, help=formtips.FEEL_HELP,
                             default=FEEL_LABEL.get(feel_item.get("feel")), on_change=_set_feel, args=(feel_item["uid"], fk))

    st.write("")
    _plan_list(sess, cur)
    st.write("")
    finish = st.button("Finish workout", type="primary" if not cur else "secondary", width="stretch", disabled=done == 0,
                       icon=":material/flag:")
    if done == 0:
        st.caption("Each set is saved when you tap Done. Sets you skip aren't.")
    if st.button("Change today's plan", icon=":material/tune:", key=f"{sess['id']}:lineup", type="tertiary"):
        _open_editor(sess)
        st.rerun()  # your logged sets stay

    if finish or st.session_state.pop("t_finish_now", False):
        with st.spinner("Saving your workout..."):
            summary = _finish(username, sess)
        import gifs
        gifs.new_round("done")
        gifs.new_round("pr")
        st.session_state.update(t_summary=summary, t_phase="landing")
        st.session_state.pop("sess", None)
        session_data.clear_live(username)
        st.session_state.pop("cel_saved", None)
        ui.forget("t_lineup_")  # next workout starts from a fresh, rotated lineup
        st.session_state.pop("t_extras", None)
        st.rerun()


def _count_skill_practice(username, lid, results):
    """A skill block's step, done inside a workout, counts as a practice: same 2-in-a-row rule as Skills."""
    lad = sk.all_ladders(session_data.custom_skills(username)).get(lid)
    states = dict(session_data.skills(username))
    if not lad or lid not in states or not results:
        return ""
    gs = states[lid]
    step = lad["steps"][min(gs["step"], len(lad["steps"]) - 1)]
    ev = sk.evaluate(step, results)
    new, event = sk.advance(gs, ev["hit"], len(lad["steps"]))
    states[lid] = new
    session_data.save_skills(username, states)
    if event == "level_up":
        return f"{lad['title']}: up to {lad['steps'][new['step']]['name']}"
    if event == "complete":
        return f"{lad['title']}: goal reached"
    if event == "clear":
        return f"{lad['title']}: target hit, once more to move up"
    return f"{lad['title']}: practice logged"


def _finish(username, sess):
    unit = sess["unit"]
    performed_at = datetime.now().isoformat(timespec="seconds")
    rows, prs, volume, n_sets, milestones, reps_total = [], [], 0.0, 0, [], 0
    skill_rows, stretch_rows = [], []
    first_ever = not session_data.all_sets(username)
    for item in sess["items"]:
        done = _done_rows(item, unit)
        if not done:
            continue
        lift = item["lift"]
        if lift.get("phase"):  # warm-up or cool-down: logged as stretching, never a lift or a record
            for n, d in enumerate(done, 1):
                stretch_rows.append({"exercise": item["exercise"], "set_no": n, "weight": 0.0, "reps": d["reps"], "is_pr": False})
                n_sets += 1
                reps_total += 0 if lift.get("hold") else d["reps"]  # holds are seconds, not reps
            continue
        if lift.get("skill_part"):  # skill block: logged as skill practice, and the step counts toward moving up
            for n, d in enumerate(done, 1):
                skill_rows.append({"exercise": f"Skill: {item['exercise']}", "set_no": n, "weight": 0.0,
                                   "reps": d["reps"], "is_pr": False})
                n_sets += 1
                reps_total += 0 if lift.get("hold") else d["reps"]
            if lift.get("skill"):
                note = _count_skill_practice(username, lift["skill"], [d["reps"] for d in done])
                if note:
                    milestones.append(note)
            continue
        if lift.get("hold"):  # logged by time; never a "lift" to progress. A longer hold than ever is a record.
            best = _best_hold(item)
            top = max(d["reps"] for d in done)
            for n, d in enumerate(done, 1):
                is_pr = bool(best) and d["reps"] == top and top > best
                rows.append({"exercise": item["exercise"], "set_no": n, "weight": 0.0, "reps": d["reps"], "is_pr": is_pr})
                n_sets += 1
            if best and top > best:
                prs.append({"exercise": item["exercise"], "kind": "hold", "weight": 0, "reps": top, "before": best})
            continue
        flags, best = training.find_prs(item["prev"], done, lift.get("pr_weight"), lift.get("pr_reps"))
        for n, (d, kind) in enumerate(zip(done, flags), 1):
            rows.append({"exercise": item["exercise"], "set_no": n, "weight": d["weight"], "reps": d["reps"], "is_pr": bool(kind)})
            volume += d["weight"] * d["reps"]
            reps_total += d["reps"]
            n_sets += 1
        if best:
            before = max([s["weight"] for s in item["prev"]] + [lift.get("pr_weight") or 0])
            prs.append({**best, "exercise": item["exercise"], "before": before or None})
            if best["kind"] == "weight":
                label = training.milestone_crossed(before, best["weight"], unit)
                if label:
                    milestones.append(f"{item['exercise']}: {label}")
        top = max(done, key=lambda d: (d["weight"], d["reps"]))
        if lift.get("pr_weight") is None or top["weight"] > lift["pr_weight"] + training.EPS:  # keep the baseline current
            session_data.upsert_lift(
                username, item["exercise"], lift["day_type"], top["weight"], top["reps"],
                lift["rep_low"], lift["rep_high"], lift["sets"],
            )
    if rows:
        session_data.log_sets(username, sess["id"], performed_at, sess["day"], rows)
    if skill_rows:
        session_data.log_sets(username, uuid.uuid4().hex, performed_at, "skill", skill_rows)
    if stretch_rows:
        session_data.log_sets(username, uuid.uuid4().hex, performed_at, "stretch", stretch_rows)
    titles = dict(session_data.settings(username).get("session_titles") or {})  # what each workout was called
    titles[sess["id"]] = sess.get("source") or training.DAY_LABELS.get(sess["day"], "Workout")
    session_data.save_settings(username, last_source=sess.get("source"), session_titles=titles)
    feels = dict(session_data.settings(username).get("feels", {}))
    feels.update({i["exercise"]: i["feel"] for i in sess["items"] if i.get("feel") and _done_rows(i, unit)})
    if feels != session_data.settings(username).get("feels", {}):
        session_data.save_settings(username, feels=feels)
    minutes = max(1, round(_workout_seconds(sess) / 60))  # time training, not counting pauses
    week, _ = training.streak_summary(session_data.all_sets(username))
    # how special was today? quiet by default, expressive when earned
    tier = "big" if (first_ever or milestones or len(prs) >= 2) else "pr" if prs else "none"
    return {"names": [i["exercise"] for i in sess["items"] if _done_rows(i, unit)], "source": sess.get("source"),
            "from": sess.get("from"),
            "prs": prs, "sets": n_sets, "volume": volume, "reps": reps_total, "minutes": minutes, "unit": unit, "day": sess["day"],
            "tier": tier, "first_ever": first_ever, "milestones": milestones, "week": week,
            "next": training.suggest_split(sess["day"], any(l["day_type"] == "upper" for l in session_data.lifts(username)),
                                           any(l["day_type"] == "lower" for l in session_data.lifts(username)))}


@st.dialog("Workout complete", width="large")
def celebrate(username, summary, pages):
    unit, tier = summary["unit"], summary["tier"]

    cards = []
    for p in summary["prs"]:
        if p["kind"] == "hold":
            cards.append({"title": p["exercise"], "big": amount(0, p["reps"], unit, "hold"),
                          "badge": f"+{p['reps'] - p['before']} s", "note": f"Longest hold · was {p['before']} s"})
            continue
        up = p["kind"] == "weight" and p["before"]
        cards.append({
            "title": p["exercise"],
            "big": amount(p["weight"], p["reps"], unit),
            "badge": f"+{training.fmt_weight(p['weight'] - p['before'], unit)}" if up else None,
            "note": ("Heaviest ever" if p["kind"] == "weight" else "Most reps ever" if not p["weight"] else "Most reps at this weight")
                    + (f" · was {training.fmt_weight(p['before'], unit)}" if up else ""),
        })
    chips = list(summary["milestones"])
    if summary["first_ever"]:
        chips.insert(0, "Your first workout is in the books")
    if summary["week"] >= 1:
        chips.append(f"{summary['week']} workout{'s' if summary['week'] != 1 else ''} this week")
    n = len(summary["prs"])
    sub = (f"{n} new personal record{'s' if n != 1 else ''}" if n
           else "Every walk counts toward your week." if summary.get("day") == "cardio"
           else "Stretching adds up across the week. Nice work making time for it." if summary.get("day") == "stretch"
           else "Today's numbers are your baseline. Next time, you're aiming to beat them." if summary["first_ever"]
           else "No PR today, and that's fine. Showing up is what builds the next one.")
    st.html(celebration.render(tier, celebration.headline(tier), sub, cards, chips))
    import gifs
    if gifs.enabled(username):  # a little fun, G-rated (GIPHY); the flame above stays either way
        gifs.show(username, "pr" if summary["prs"] else "done", height=170)

    # Three numbers, never a zero: a stat that doesn't apply (no weights, under a minute) gives way to one that does.
    pool = [("Sets", summary["sets"]),
            ("Total lifted", f"{round(training.to_unit(summary['volume'], unit)):,} {unit}") if summary["volume"] else None,
            ("Reps", f"{summary.get('reps', 0):,}") if summary.get("reps") else None,
            ("Minutes", summary["minutes"]) if summary["minutes"] else None,
            ("Exercises", len(summary.get("names") or [])) if summary.get("names") else None,
            ("Records", len(summary["prs"])) if summary["prs"] else None] + list(summary.get("extra") or [])
    stats = [x for x in pool if x and x[1]][:3]
    st.html('<div style="display:flex;justify-content:space-between;gap:.5rem;margin:.4rem 0 .6rem;text-align:center">'
            + "".join(f'<div style="flex:1"><div style="font-size:1.6rem;font-weight:800;letter-spacing:-.02em">{v}</div>'
                      f'<div style="font-size:.78rem;opacity:.65">{k}</div></div>' for k, v in stats) + "</div>")
    if summary.get("day") == "cardio":
        st.caption("Walking minutes add up across the week. Your plan on Home shows what's next.")
    elif summary.get("day") == "stretch":
        st.caption("Stretch on at least 2 or 3 days a week; total time per week is what counts most.")
    elif summary.get("source"):  # a curated workout or saved routine: repeating it is the plan (2-3 days a week)
        st.caption(f"Next time: {summary['source']} again in 2 or 3 days, aiming for one more rep. "
                   "Or pick something new from Workout.")
    else:
        st.caption(f"Next time we'll suggest {training.DAY_LABELS[summary['next']].lower()}. "
                   "Rest a day before training the same muscles hard again.")

    if summary.get("names") and not summary.get("source"):
        done = st.session_state.get("cel_saved")
        if done:
            minis = prepare_minis([e for e in (find_exercise(n) for n in summary["names"]) if e])
            ui.saved(f"Saved as {done}", "It's in your playlists, ready to start next time.", [minis.get(n) for n in summary["names"]])
        else:
            name = st.text_input("Save this workout as a playlist (optional)", placeholder="e.g. My Monday upper", key="cel_rt")
            if st.button("Save playlist", icon=":material/bookmark_add:", key="cel_rt_save", disabled=not (name or "").strip()):
                for ex in summary["names"]:
                    session_data.add_routine(username, name.strip(), [ex], 3, 8, 0)
                st.session_state.update(cel_saved=name.strip(), t_summary=summary)  # keep this screen open
                st.rerun()
    a, b = st.columns(2)
    back = summary.get("from") if summary.get("from") in pages else "home"  # back to where you started it
    if a.button("Done", type="primary", width="stretch", key="cel_done"):
        ui.go(back)
    if b.button("See progress", width="stretch", key="cel_prog"):
        ui.go("progress")
