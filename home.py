"""Home: the personal front door. It changes with who you are and what you're here for.

New here: a choice of three starting points (you steer, nothing is locked in).
Returning: this week's flames, one clear next action, and your own goals.
"""
import html
from datetime import date, datetime, timedelta

import streamlit as st

import onboarding
import plan as week_plan
import session_data
import skills_logic as sk
import training
import ui
from exercise_data import find_exercise, mini_url, prepare_minis, anim_url, thumb_url

def _thumb(name):
    ex = find_exercise(name) if name else None
    return mini_url(ex) if ex else None


def _greeting():
    h = datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening"


def home_page(username, pages):
    sets = session_data.all_sets(username)
    lifts = session_data.lifts(username)
    ladders = sk.all_ladders(session_data.custom_skills(username))
    skills = {k: v for k, v in session_data.skills(username).items() if k in ladders}
    settings = session_data.settings(username)

    fresh = not (lifts or skills or sets)
    if st.session_state.get("ob_welcome") or st.session_state.get("ob_replay") or (fresh and not settings.get("onboarded")):
        onboarding.onboarding(username, pages, settings)
        return

    st.caption(date.today().strftime("%A, %d %B"))
    who = st.session_state.get("display", "")
    st.title(f"{_greeting()}, {who}" if who else _greeting())

    returning(username, pages, sets, lifts, ladders, skills, settings)


# --- everyone else ------------------------------------------------------------------------
def returning(username, pages, sets, lifts, ladders, skills, settings):
    """Status first (this week), then the one thing to do now, then what you're building toward."""
    goal = int(settings.get("weekly_goal", 3))
    dots = training.week_dots(sets)
    done_days = sum(dots)

    ui.flames(dots)
    left = max(0, goal - done_days)
    st.html(f'<p class="bs-week"><b>{done_days} of {goal} days</b> this week'
            + (" · goal reached" if not left else f" · {left} to go") + "</p>")

    sessions = training.group_sessions(training.strength_sets(sets))
    away = training.days_since(sessions[0]["performed_at"]) if sessions else 0
    if away >= 14:  # never punish absence: nothing resets, weights ease in (training.suggest handles that)
        st.html(f'<p class="bs-back"><b>Welcome back.</b> Your last workout was {html.escape(training.break_label(away))}. '
                "Your records are safe, and today's weights start a little lighter so you can build back up.</p>")

    # a walk counts toward the week (the flames), but doesn't tick off today's workout
    trained_today = training.week_dots([x for x in sets if not x["exercise"].startswith("Walk:")])[date.today().weekday()]
    focus = settings.get("focus", "strength" if lifts else "skills" if skills else "explore")

    wp = week_plan.get(username)
    if "sess" in st.session_state:
        in_progress(pages)
        if wp:
            st.markdown("##### This week")
            import lifts as library
            library._week_rows(username, pages, wp)
    elif wp:
        planned_today(username, pages, wp, dots, trained_today)
    elif not trained_today and _rest_day(sets, done_days, goal):
        rest_block(pages)
        walk_card(username, sets)
    else:
        next_up(username, pages, sets, lifts, trained_today)
        walk_card(username, sets)
    if not wp:
        plan_prompt(pages)
    blocks = [lambda: skills_block(pages, ladders, skills), lambda: records_block(pages, sets, session_data.unit(username))]
    if focus != "skills":
        blocks.reverse()
    for block in blocks:
        block()


WALK_CSS = """<style>
.bs-walk { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border-radius: 16px; margin: .2rem 0 .6rem;
  background: var(--bs-accent-soft); }
.bs-walk .ic { font-family: 'Material Symbols Rounded'; font-size: 30px; color: var(--bs-accent-ink); }
.bs-walk .t { font-weight: 700; } .bs-walk .d { font-size: .85rem; opacity: .75; }
.bs-walk.done .ic { color: #16a34a; }
</style>"""


def walk_card(username, sets):
    """Today's walking habit (Plan my week), on top of whatever else today holds. Tick it off when it's done."""
    steps = week_plan.walk_today(username, date.today().weekday())
    if not steps:
        return
    today = date.today().isoformat()
    done = any(s["exercise"].startswith("Walk:") and s["performed_at"][:10] == today for s in sets)
    st.html(WALK_CSS + f'<div class="bs-walk{" done" if done else ""}"><span class="ic">'
            f'{"check_circle" if done else "directions_walk"}</span><div><div class="t">'
            f'{"Walk done" if done else f"Walk {steps:,} steps today"}</div><div class="d">'
            f'{"Nice. It counts toward your week." if done else "Part of your walking habit. Any walk counts."}'
            '</div></div></div>')
    if not done and st.button("I did my walk", icon=":material/check:", key="home_walk_done", width="stretch"):
        import uuid
        from datetime import datetime

        mins = max(10, round(steps / 100))  # about 100 steps a minute at a brisk pace
        session_data.log_sets(username, uuid.uuid4().hex, datetime.now().isoformat(timespec="seconds"), "cardio",
                              [{"exercise": f"Walk: {steps:,} steps", "set_no": 1, "weight": 0.0, "reps": mins,
                                "is_pr": False}])
        st.toast(f"Walk logged: {steps:,} steps (about {mins} minutes)", icon=":material/directions_walk:")
        st.rerun()


def plan_prompt(pages):
    """No plan yet: one quiet row that says what planning gets you."""
    with st.container(key="home-plan-box"):
        st.markdown("**Plan your week**")
        st.caption("Pick your days once. Then this page shows today's workout, ready to start.")
        if st.button("Plan my week", icon=":material/calendar_month:", key="home_plan"):
            for k in [k for k in st.session_state if k.startswith("wp_")]:
                del st.session_state[k]
            st.session_state["t_phase"] = "plan"
            ui.to_workout(pages)
    st.write("")


def _planned_hero(username, pages, key, kicker, button, bkey, primary=True, day=None):
    d = week_plan.describe(username, key)
    if not d:
        return False
    title, img, meta, rows = d
    extra = week_plan.day_skill(username, day) if day is not None else None
    if extra:  # a skill practice added to this day runs after the workout
        sd = week_plan.describe(username, extra)
        if sd:
            title, rows = f"{title} + {sd[0]}", rows + [(None, f"{sd[0]} practice", sd[2])]
    ui.hero(kicker, title, meta, img)
    if primary and not key.startswith(("walk:", "sk:")):  # same options as every workout card on Home
        def light_start(light):
            st.session_state["t_light"] = light
            week_plan.start(username, pages, key, day)
        _alt_row(username, pages, light_start)
    ui.tracklist(rows)
    st.write("")
    st.html(HOME_CSS)
    with st.container(key="bs-homestart"):
        go = st.button(button, type="primary" if primary else "secondary", icon=":material/play_arrow:", key=bkey,
                       width="stretch")
    if go:
        week_plan.start(username, pages, key, day)
    return True


def planned_today(username, pages, wp, dots, trained_today):
    """With a plan: today's workout (or rest), then the week. Nothing is ever marked missed."""
    today_i = date.today().weekday()
    key = wp.get(str(today_i))
    nxt = week_plan.next_planned(wp)
    when = lambda d: "tomorrow" if d == (today_i + 1) % 7 else week_plan.DAYS[d]
    if key and not trained_today:
        _planned_hero(username, pages, key, "Today",
                      "Start practice" if key.startswith("sk:") else "Start walk" if key.startswith("walk:") else "Start",
                      "home_plan_go", day=today_i)
    elif trained_today:
        st.html('<p class="bs-week"><b>Done for today.</b> Rest and recovery are part of getting stronger.'
                + (f" Next: {html.escape(week_plan.label(username, nxt[1]))}, {when(nxt[0])}." if nxt else "") + "</p>")
    else:
        st.html('<p class="bs-week"><b>Rest day.</b> '
                + (f"Next: {html.escape(week_plan.label(username, nxt[1]))}, {when(nxt[0])}." if nxt else "") + "</p>")
        a, b = st.columns(2)
        if a.button("5-minute stretch", icon=":material/self_improvement:", key="home_plan_stretch", width="stretch"):
            import today
            today.start_stretch(username, pages)
        if nxt and b.button("Do next workout now", icon=":material/play_arrow:", key="home_plan_early", width="stretch"):
            week_plan.start(username, pages, nxt[1], nxt[0])
    walk_card(username, session_data.all_sets(username))
    st.markdown("##### This week")
    import lifts as library
    library._week_rows(username, pages, wp)
    if st.button("Edit my week", icon=":material/edit_calendar:", key="home_plan_edit", type="tertiary"):
        for k in [k for k in st.session_state if k.startswith("wp_")]:
            del st.session_state[k]
        st.session_state.update(t_phase="plan", wp_step=3)
        ui.to_workout(pages)
    st.write("")


def in_progress(pages):
    """A workout you started and left: pick it up exactly where you were."""
    import today

    sess = st.session_state["sess"]
    total = sum(len(i["rows"]) for i in sess["items"])
    done = sum(1 for i in sess["items"] for r in i["rows"] if r["d"])
    cur = today._current(sess)
    ex = find_exercise(cur["exercise"]) if cur else None
    state = "Paused" if sess.get("paused_at") else "Ready to start" if sess.get("ready") else "In progress"
    ui.hero(state, sess.get("source") or training.DAY_LABELS.get(sess["day"], "Workout"),
            f"{done} of {total} sets done" + (f"  ·  next: {cur['exercise']}" if cur else ""), anim_url(ex, labels=False) if ex else None)
    st.write("")
    st.html(HOME_CSS)
    with st.container(key="bs-homestart"):
        go = st.button("Resume workout" if sess.get("paused_at") else "Continue workout", type="primary",
                       icon=":material/play_arrow:", key="home_resume", width="stretch")
    if go:
        st.session_state.update(t_phase="session", t_go_session=True)
        ui.to_workout(pages)
    st.write("")


def _rest_day(sets, done_days, goal):
    """A rest day is a guess (we don't know your schedule): two days in a row, or the weekly goal is met."""
    days = {datetime.fromisoformat(s["performed_at"]).date() for s in sets}
    today = date.today()
    back_to_back = (today - timedelta(days=1)) in days and (today - timedelta(days=2)) in days
    return back_to_back or done_days >= goal


def rest_block(pages):
    """Rest day: gentle movement counts as rest. One tap starts a 5-minute stretch with demos and hold clocks."""
    import today

    names = today.COOLDOWNS["full"]
    exs = [e for e in (find_exercise(n) for n in names) if e]
    minis = prepare_minis(exs) if exs else {}
    ui.hero("Rest day", "Move gently", "Easy stretches count as rest. About 5 minutes.", anim_url(exs[0], labels=False) if exs else None)
    ui.tracklist([(minis.get(n), n, "Hold 30 seconds") for n in names])
    st.write("")
    if st.button("Start 5-minute stretch", type="primary", icon=":material/self_improvement:", key="home_rest_go",
                 width="stretch"):
        today.start_stretch(st.session_state["username"], pages)
    if st.button("Train anyway", icon=":material/fitness_center:", key="home_train_anyway"):
        ui.to_workout(pages)
    st.write("")


def _ago(days):
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago" if days < 14 else training.break_label(days)


STARTER = "full-bodyweight"  # no equipment, beginner-friendly: a first workout anyone can do (curated_workouts.json)


def starter(username, pages, trained_today=False):
    """Too few lifts tracked to build a plan: offer a ready-made workout (the last one you did, else the starter)."""
    import today

    last = session_data.settings(username).get("last_source")
    w = (next((x for x in today.curated() if x["title"] == last), None)
         or next((x for x in today.curated() if x["id"] == STARTER), None))
    if not w:
        return
    done_before = w["title"] == last
    exercises = [find_exercise(e[0]) for e in w["exercises"]]
    exercises = [e for e in exercises if e]
    minis = prepare_minis(exercises) if exercises else {}
    mins = today.workout_minutes(w)
    kicker = "Trained today" if trained_today else "Up next" if session_data.all_sets(username) else "Your first workout"
    ui.hero(kicker, w["title"], f"{len(w['exercises'])} moves  ·  about {mins} min",
            today.cover_url(w) or None)
    if not trained_today:
        def light_start(light):
            st.session_state["t_light"] = light
            today._start_template(username, w)
            ui.to_workout(pages)
        _alt_row(username, pages, light_start)
    ui.tracklist([(minis.get(e[0]), e[0], f"{e[1]} sets · {e[2]} s hold" if e[4:] == ["hold"] else f"{e[1]} sets · {e[2]}-{e[3]} reps")
                  for e in w["exercises"]])
    st.write("")
    if done_before:
        st.caption("Same workout. Aim for one more rep.")
    st.html(HOME_CSS)
    with st.container(key="bs-homestart"):
        if st.button("Do it again" if trained_today else "Start workout", type="primary", icon=":material/play_arrow:",
                     key="home_starter", width="stretch"):
            today._start_template(username, w)
            ui.to_workout(pages)
    st.write("")


def next_up(username, pages, sets, lifts, trained_today):
    if not lifts:
        starter(username, pages, trained_today)
        return
    strength = training.strength_sets(sets)
    sessions = training.group_sessions(strength)
    last_day = sessions[0]["day_type"] if sessions else None
    day = training.suggest_split(
        last_day, any(l["day_type"] == "upper" for l in lifts), any(l["day_type"] == "lower" for l in lifts)
    )
    names = training.pick_lineup(lifts, day, strength, 4)
    if len(lifts) < 3 or len(names) < 2:  # one or two tracked lifts don't make a workout yet
        starter(username, pages, trained_today)
        return
    by_name = {l["exercise"]: l for l in lifts}
    same = [s for s in sessions if s["day_type"] == day]
    meta = f"last trained {_ago(training.days_since(same[0]['performed_at']))}" if same else "not trained yet"

    exercises = [find_exercise(n) for n in names if find_exercise(n)]
    minis = prepare_minis(exercises) if exercises else {}
    n_ex = len(names)
    import today  # rest lengths live with the session (research.json)

    secs = sum(by_name[n]["sets"] * (40 + today.rest_seconds(n)) for n in names)  # ~40 s per set plus its rest
    mins = max(5, int(round(secs / 60 / 5.0)) * 5)
    ui.hero(
        "Trained today" if trained_today else "Up next", training.DAY_LABELS[day],
        f"{n_ex} move{'s' if n_ex != 1 else ''}  ·  about {mins} min  ·  {meta}", anim_url(exercises[0], labels=False) if exercises else None,
    )
    if not trained_today:
        _alt_row(username, pages, lambda light: _go_day(username, pages, day, names, light))
    ui.tracklist([
        (minis.get(n), n, f"{by_name[n]['sets']} sets · {by_name[n]['rep_low']}-{by_name[n]['rep_high']} reps")
        for n in names
    ])
    st.write("")
    with st.container(key="bs-homestart"):
        if st.button("Do it again" if trained_today else "Start workout", type="primary", icon=":material/play_arrow:",
                     key="home_start", width="stretch"):
            _go_day(username, pages, day, names, False)
    st.write("")


HOME_CSS = """<style>
.st-key-bs-homestart .stButton { margin-inline: auto; max-width: 480px !important; }
.st-key-bs-homestart button { height: 56px; border-radius: 999px !important; font-size: 1.05rem; }
.st-key-keep-home-alt [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .4rem; margin-top: -.2rem; }
.st-key-keep-home-alt [data-testid="stColumn"] { flex: 0 0 auto !important; width: auto !important; }
.st-key-keep-home-alt button p { font-size: .88rem !important; }
</style>"""


def _alt_row(username, pages, light_start):
    """Right under the card: swap it for another workout, or do this one lighter today."""
    st.html(HOME_CSS)
    with st.container(key="keep-home-alt"):
        a, b, _ = st.columns([1, 1, 1])
        if a.button("Change workout", icon=":material/swap_horiz:", key="home_change", type="tertiary"):
            st.session_state["t_phase"] = "day"
            ui.to_workout(pages)
        if b.button("Not feeling it today", icon=":material/spa:", key="home_light", type="tertiary",
                    help="Same workout, about half the sets and a little lighter"):
            light_start(True)


def _go_day(username, pages, day, names, light):
    import today

    st.session_state.update(t_day=day, t_light=light)
    today._begin(username, names)
    ui.to_workout(pages)


def skills_block(pages, ladders, skills):
    active = [(ladders[k], v) for k, v in skills.items() if not v.get("done")]
    if not active:
        return
    st.markdown("##### Skills you're working on")
    for lad, gs in active[:3]:
        steps = lad["steps"]
        i = min(gs["step"], len(steps) - 1)
        with st.container(key=f"keep-sk-{lad['id']}"):
            pic, text, act = st.columns([1, 5, 2])
            thumb = _thumb(steps[i].get("library"))
            if thumb:
                with pic:
                    ui.thumb(thumb, "sm")
            text.markdown(f"**{lad['title']}**")
            text.caption(f"Step {i + 1} of {len(steps)}: {steps[i]['name']} · {sk.target_text(steps[i])}")
            if act.button("Practice", key=f"home_sk_{lad['id']}", icon=":material/play_arrow:"):
                import skills as skills_page_mod  # opens the guided practice straight away

                skills_page_mod.start_practice(lad)
                st.switch_page(pages["skills"])
    st.write("")


def records_block(pages, sets, unit):
    prs = [s for s in sets if s["is_pr"]]
    if not prs:
        return
    st.markdown("##### Recent personal records")
    rows, seen = [], set()
    for s in reversed(prs):
        if s["exercise"] in seen:
            continue
        seen.add(s["exercise"])
        ago = (date.today() - datetime.fromisoformat(s["performed_at"]).date()).days
        rows.append((_thumb(s["exercise"]), s["exercise"],
                     f"{training.amount(s['weight'], s['reps'], unit, training.kind_of(s['exercise'], s.get('day_type')))}  ·  {_ago(ago)}"))
        if len(rows) == 3:
            break
    ui.tracklist(rows, numbered=False)
    st.page_link(pages["progress"], label="See all your progress", icon=":material/arrow_forward:")
    st.write("")
