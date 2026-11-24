"""Plan my week: pick what goes on each day once, then Home shows today's workout ready to start.

A plan is a small dict in the person's settings: {"0": "cur:full-bodyweight", "2": "rt:My Monday", ...}
(weekday 0 = Monday). Days not in the plan are rest days. Keys:
  cur:<id>     a curated workout (curated_workouts.json)
  rt:<name>    one of your saved routines
  day:<split>  upper / lower / full, built from the lifts you track (needs 3+ lifts)
  sk:<id>      a guided skill practice (warm-up, drills, then your current step)
  walk:<kind>  a 30-minute walk: brisk, or the 12-3-30 incline walk (logged as minutes)
The planner asks: how many days, which days, and your goal; then it fills in a week to review.
Training on a different day still counts: the plan is a guide, never a streak to break.
"""
from datetime import date

import streamlit as st

import session_data
import skills_logic as sk
import training
import ui
from exercise_data import find_exercise, mini_url, prepare_minis, anim_url, thumb_url

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
REST = "rest"
STARTER = "cur:full-bodyweight"
# Spread training days out so muscles get a day between sessions (Mon/Wed/Fri for 3, and so on).
SPREAD = {1: [2], 2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 2, 4, 5], 6: [0, 1, 2, 3, 4, 5], 7: list(range(7))}
MIN_LIFTS = 3  # fewer tracked lifts than this don't make a workout of their own

# Goals and what the suggested week does for each (research ids in research.json; shown as "Why this plan").
GOALS = {  # id: (label, what it puts in your week, research ids whose "what to do" lines explain it)
    "muscle": ("Build muscle", "Strength days that train each muscle twice a week.", ["volume-hypertrophy", "frequency-2x"]),
    "strength": ("Get stronger", "Full-body strength days, adding weight over time.", ["novice-total-body", "progression-top-of-range"]),
    "lose": ("Lose weight", "Strength to keep muscle, plus walks to move more.", ["weight-loss-activity", "strength-keeps-muscle"]),
    "maintain": ("Keep my weight", "Two strength days and regular walks.", ["who-activity", "strength-keeps-muscle"]),
    "healthy": ("Stay healthy", "Two strength days and regular walks.", ["who-activity", "steps-mortality"]),
    "endurance": ("Build stamina", "Walks on most days, with strength to back them up.", ["who-activity", "steps-mortality"]),
    "mobility": ("Move better", "Stretch sessions on easy days.", ["stretch-weekly", "stretch-hold"]),
    "skill": ("Learn a skill", "Practise your skill, with strength days to back it up.", ["novice-total-body", "frequency-2x"]),
}
STRETCH_DAY = "cur:stretch-full"
WALK_PICTURE = {"brisk": "Trail Running/Walking", "incline": "Walking, Treadmill"}  # library demos, so a walk is never blank
FROM_ONBOARDING = {GOALS[g][0]: g for g in GOALS}  # onboarding uses the same labels: "Build muscle" -> "muscle"
WALKS = {
    "brisk": ("Brisk walk", "30 minutes at a pace where you can talk but not sing",
              [("Easy start", "5 min"), ("Brisk", "20 min, breathing harder but able to talk"), ("Easy finish", "5 min")]),
    "incline": ("Incline walk (12-3-30)", "30 minutes on a treadmill: 12% incline, 3 mph",
                [("Warm up flat", "3 to 5 min"), ("Incline 12%, 3 mph", "30 min (lower either if you need to)"),
                 ("Cool down flat", "3 to 5 min")]),
}


def _ladders(username):
    return sk.all_ladders(session_data.custom_skills(username))


def _active_skills(username):
    lads = _ladders(username)
    return [(lid, lads[lid]) for lid, s in session_data.skills(username).items() if lid in lads and not s.get("done")]


def options(username):
    """Everything that can go on a day: [(key, label)], rest first."""
    import today

    out = [(REST, "Rest")]
    out += [(f"rt:{n}", f"{n} (my playlist)") for n in session_data.routines(username)]
    if len(session_data.lifts(username)) >= MIN_LIFTS:
        out += [(f"day:{d}", label) for d, label in (("upper", "Upper body"), ("lower", "Lower body"),
                                                                         ("full", "Full body"))]
    out += [(f"cur:{w['id']}", w["title"]) for w in today.curated()]
    out += [(f"sk:{lid}", f"Practise: {lad['title']}") for lid, lad in _active_skills(username)]
    out += [(f"walk:{k}", v[0]) for k, v in WALKS.items()]
    return out


def get(username):
    """The saved plan with anything that no longer exists (a removed routine or skill) dropped."""
    raw = session_data.settings(username).get("week_plan") or {}
    valid = {k for k, _ in options(username)}
    return {d: k for d, k in raw.items() if k in valid and k != REST}


def save(username, plan):
    session_data.save_settings(username, week_plan={d: k for d, k in plan.items() if k and k != REST})


def default_goals(username):
    """Your goals for the week, most important first (a list; older saves stored one goal)."""
    g = session_data.settings(username).get("plan_goal")
    goals = [x for x in (g if isinstance(g, list) else [g]) if x in GOALS]
    if not goals:  # not planned yet: start from what they picked in onboarding
        goals = [FROM_ONBOARDING[x] for x in session_data.settings(username).get("goals") or [] if x in FROM_ONBOARDING]
    return goals or [default_goal(username)]


def default_goal(username):
    g = session_data.settings(username).get("plan_goal")
    if isinstance(g, list):
        g = next((x for x in g if x in GOALS), None)
    if g in GOALS:
        return g
    for label_ in session_data.settings(username).get("goals") or []:  # what they picked in onboarding
        if label_ in FROM_ONBOARDING:
            return FROM_ONBOARDING[label_]
    return "strength"


def default_days(username, count=None):
    plan = get(username)
    if plan and count is None:
        return sorted(int(d) for d in plan)
    n = count or max(1, min(7, int(session_data.settings(username).get("weekly_goal", 3))))
    return SPREAD[n]


def _lift_keys(username, n):
    """n strength sessions: whole body for up to 3 days (ACSM novice-total-body), upper and lower alternating for
    4+ when there are enough tracked lifts (each trained twice: frequency-2x)."""
    if len(session_data.lifts(username)) >= MIN_LIFTS:
        return (["day:upper", "day:lower"] * 4)[:n] if n >= 4 else ["day:full"] * n
    import today

    last = session_data.settings(username).get("last_source")
    cur = next((f"cur:{w['id']}" for w in today.curated() if w["title"] == last and w["focus"] == "full"), STARTER)
    return [cur] * n


def _spaced(days, n):
    """Pick n of the chosen days as far apart as possible (strength days need a day between)."""
    if n >= len(days):
        return list(days)
    if n == 1:
        return [days[0]]
    return [days[round(i * (len(days) - 1) / (n - 1))] for i in range(n)]  # first to last, evenly


def suggest(username, days=None, goal=None):
    """A week from the chosen days and goals. The first goal decides the main days; the others add light extras
    (a walk, a stretch, a skill practice) on days left free. Routines are never guessed in."""
    goals = goal if isinstance(goal, list) else [goal or default_goal(username)]
    goals = [g for g in goals if g in GOALS] or ["strength"]
    main = {"maintain": "healthy", "endurance": "healthy", "mobility": "healthy"}.get(goals[0], goals[0])
    days = sorted(days if days is not None else default_days(username))
    n = len(days)
    plan = {}
    if main == "lose":  # keep strength (muscle), add walking minutes (weight-loss-activity)
        lift_days = _spaced(days, min(3, max(1, (n + 1) // 2)))
        for d, k in zip(lift_days, _lift_keys(username, len(lift_days))):
            plan[str(d)] = k
        for d in days:
            plan.setdefault(str(d), "walk:brisk")
    elif main == "healthy":  # WHO: muscle strengthening plus 150-300 aerobic minutes
        lift_days = _spaced(days, min(2, n))
        for d, k in zip(lift_days, _lift_keys(username, len(lift_days))):
            plan[str(d)] = k
        filler = STRETCH_DAY if goals[0] == "mobility" else "walk:brisk"
        for d in days:
            plan.setdefault(str(d), filler)
    elif main == "skill" and _active_skills(username):
        skill_id = _active_skills(username)[0][0]
        lift_days = _spaced(days, n // 2) if n >= 2 else []
        for d, k in zip(lift_days, _lift_keys(username, len(lift_days))):
            plan[str(d)] = k
        for d in days:
            plan.setdefault(str(d), f"sk:{skill_id}")
    else:  # strength, muscle (and skill with no skill chosen yet)
        for d, k in zip(days, _lift_keys(username, n)):
            plan[str(d)] = k
    free = [d for d in range(7) if str(d) not in plan]
    extras = []  # light extras for the other goals, on free days only
    if any(g in goals[1:] for g in ("lose", "maintain", "healthy", "endurance")):
        extras.append("walk:brisk")
    if "mobility" in goals[1:]:
        extras.append(STRETCH_DAY)
    skills = _active_skills(username)
    if skills and main != "skill" and ("skill" in goals or not goals[1:]):
        extras.append(f"sk:{skills[0][0]}")  # a skill you're working on gets one light practice
    for k, d in zip(extras, _spaced(free, len(extras)) if free else []):
        plan[str(d)] = k
    return plan


def walk_minutes(plan):
    return 30 * sum(1 for k in plan.values() if k.startswith("walk:"))


def label(username, key):
    return dict(options(username)).get(key, "Rest").replace(" (my playlist)", "")


def describe(username, key):
    """(title, image_url, meta, rows) for a planned item, rows = [(mini_url, name, detail)]."""
    import today

    kind, _, ref = key.partition(":")
    if kind == "walk" and ref in WALKS:
        title, meta, steps = WALKS[ref]
        ex = find_exercise(WALK_PICTURE[ref])
        mini_ = mini_url(ex) if ex else None
        return title, anim_url(ex, labels=False) if ex else None, meta, [(mini_, a, b) for a, b in steps]
    if kind == "cur":
        w = next((x for x in today.curated() if x["id"] == ref), None)
        if not w:
            return None
        cover = today.cover_url(w)
        names = [e[0] for e in w["exercises"]]
        details = {e[0]: f"{e[1]} sets · {e[2]} s hold" if e[4:] == ["hold"] else f"{e[1]} sets · {e[2]}-{e[3]} reps"
                   for e in w["exercises"]}
        mins = today.workout_minutes(w)
        title = w["title"]
    elif kind == "rt":
        items = session_data.routine_items(username, ref)
        names = list(dict.fromkeys(i["workout_name"] for i in items))
        if not names:
            return None
        by = {i["workout_name"]: i for i in items}
        import lifts as lifts_page
        details = {n: ("Drills, then your current step" if n.startswith("Skill: ")
                       else f"{int(by[n]['sets'] or 3)} sets · {int(by[n]['reps'] or 8)}+ reps") for n in names}
        mins = today._minutes([(n, int(by[n]["sets"] or 3)) for n in names if not n.startswith("Skill: ")]) \
            + 5 * sum(1 for n in names if n.startswith("Skill: "))
        title = ref
        labels = {n: lifts_page._label_item(username, n) for n in names}
        exs = [find_exercise(n) for n in names]
        minis = prepare_minis([e for e in exs if e])
        rows = [(minis.get(n), labels[n], details[n]) for n in names]
        first = next((e for e in exs if e), None)
        return title, anim_url(first, labels=False) if first else None, f"{len(names)} parts  ·  about {mins} min", rows
    elif kind == "day":
        lifts = session_data.lifts(username)
        strength = training.strength_sets(session_data.all_sets(username))
        names = training.pick_lineup(lifts, ref, strength, 4)
        if not names:
            return None
        by = {l["exercise"]: l for l in lifts}
        details = {n: f"{by[n]['sets']} sets · {by[n]['rep_low']}-{by[n]['rep_high']} reps" for n in names}
        mins = today._minutes([(n, by[n]["sets"]) for n in names])
        title = training.DAY_LABELS[ref]
    elif kind == "sk":
        lad = _ladders(username).get(ref)
        state = session_data.skills(username).get(ref)
        if not lad or not state:
            return None
        step = lad["steps"][min(state["step"], len(lad["steps"]) - 1)]
        parts = list(lad.get("drills") or []) + [step]
        names = [p["name"] for p in parts]
        details = {p["name"]: sk.target_text(p) for p in parts}
        libs = {p["name"]: p.get("library") for p in parts}
        exs = {n: find_exercise(libs[n]) for n in names if libs.get(n)}
        minis = prepare_minis([e for e in exs.values() if e])
        rows = [(minis.get(libs.get(n)), n, details[n]) for n in names]
        first = exs.get(step["name"]) or next(iter(exs.values()), None)
        return (f"{lad['title']}", anim_url(first, labels=False) if first else None,
                (f"{len(parts) - 1} drill{'s' if len(parts) != 2 else ''}, then {step['name']}" if len(parts) > 1
                 else f"Your step: {step['name']}"), rows)
    else:
        return None
    exs = [find_exercise(n) for n in names]
    minis = prepare_minis([e for e in exs if e])
    rows = [(minis.get(n), n, details[n]) for n in names]
    first = next((e for e in exs if e), None)
    pic = (cover if kind == "cur" else None) or (anim_url(first, labels=False) if first else None)
    return title, pic, f"{len(names)} moves  ·  about {mins} min", rows


def contents(username, key):
    """(exercise names, template {name: sets/reps}, title) for a planned workout, or None for walks and skills."""
    import today

    kind, _, ref = key.partition(":")
    if kind == "cur":
        w = next((x for x in today.curated() if x["id"] == ref), None)
        if not w:
            return None
        tpl = {e[0]: {"sets": e[1], "rep_low": e[2], "rep_high": e[3], "hold": e[4:] == ["hold"]} for e in w["exercises"]}
        return [e[0] for e in w["exercises"]], tpl, w["title"]
    if kind == "rt":
        items = session_data.routine_items(username, ref)
        names = list(dict.fromkeys(i["workout_name"] for i in items))
        tpl = {i["workout_name"]: {"sets": int(i["sets"] or 3), "rep_low": int(i["reps"] or 8),
                                   "rep_high": int(i["reps"] or 8) + 4} for i in items if not i["workout_name"].startswith("Skill: ")}
        return names, tpl, ref
    if kind == "day":
        lifts = session_data.lifts(username)
        names = training.pick_lineup(lifts, ref, training.strength_sets(session_data.all_sets(username)), 4)
        by = {l["exercise"]: l for l in lifts}
        tpl = {n: {"sets": by[n]["sets"], "rep_low": by[n]["rep_low"], "rep_high": by[n]["rep_high"]} for n in names}
        return names, tpl, training.DAY_LABELS[ref]
    return None


STEP_CHOICES = ["Off", "5,000", "6,000", "7,000", "8,000", "10,000", "12,000"]


def walk_habit(username):
    """{"steps": 10000, "days": [0, 2, 4, 5]} or None: a walk on top of whatever else is planned that day."""
    h = session_data.settings(username).get("walk_habit") or {}
    return h if h.get("steps") and h.get("days") else None


def walk_today(username, day):
    """Steps to walk on that day (an int), or None."""
    h = walk_habit(username)
    return int(h["steps"]) if h and day in h["days"] else None


def day_skill(username, day):
    """A skill practice added on top of a day's workout ('sk:<id>'), or None."""
    k = (session_data.settings(username).get("week_skill") or {}).get(str(day))
    return k if k and k.partition(":")[2] in dict(_active_skills(username)) else None


def start(username, pages, key, day=None):
    """Start a planned day. If that day also has a skill practice, it runs as one workout: the workout, then the
    skill's drills and current step."""
    extra = day_skill(username, day) if day is not None else None
    got = contents(username, key) if extra else None
    if got:
        import lifts as lifts_page

        names, tpl, title = got
        lid = extra.partition(":")[2]
        lad = _ladders(username).get(lid)
        lifts_page._start(username, pages, names + [f"Skill: {lid}"], tpl,
                          f"{title} + {lad['title'] if lad else 'skill'}", from_page=None)
        return
    _start_one(username, pages, key)


def _start_one(username, pages, key):
    """Start a planned item right away (the live workout, or the guided skill practice)."""
    import today

    kind, _, ref = key.partition(":")
    if kind == "walk":
        st.session_state.update(t_phase="walk", t_walk=ref)
        ui.to_workout(pages)
    if kind == "cur":
        w = next((x for x in today.curated() if x["id"] == ref), None)
        if w:
            today._start_template(username, w)
            ui.to_workout(pages)
    elif kind == "rt":
        import lifts as lifts_page

        items = session_data.routine_items(username, ref)
        names = list(dict.fromkeys(i["workout_name"] for i in items))
        template = {i["workout_name"]: {"sets": int(i["sets"] or 3), "rep_low": int(i["reps"] or 8),
                                        "rep_high": int(i["reps"] or 8) + 4} for i in items}
        lifts_page._start(username, pages, names, template, ref, from_page=None)
    elif kind == "day":
        lifts = session_data.lifts(username)
        strength = training.strength_sets(session_data.all_sets(username))
        st.session_state["t_day"] = ref
        today._begin(username, training.pick_lineup(lifts, ref, strength, 4))
        ui.to_workout(pages)
    elif kind == "sk":
        import skills as skills_page

        lad = _ladders(username).get(ref)
        if lad:
            skills_page.start_practice(lad)
            st.switch_page(pages["skills"])


def next_planned(plan, after=None):
    """(weekday, key) of the next planned day after `after` (default today), wrapping into next week."""
    if not plan:
        return None
    start_day = date.today().weekday() if after is None else after
    for step in range(1, 8):
        d = (start_day + step) % 7
        if str(d) in plan:
            return d, plan[str(d)]
    return None


def mini(username, key):
    """A small picture for a planned item (first exercise), or None."""
    d = describe(username, key)
    return d[3][0][0] if d and d[3] else None


def week_html(username, plan, dots):
    """This week's planned days as quiet rows: day, what, and a tick when you trained that day."""
    import html

    today_i = date.today().weekday()
    rows = []
    for d in range(7):
        key = plan.get(str(d))
        if not key:
            continue
        state = "done" if dots[d] else "today" if d == today_i else "past" if d < today_i else ""
        mark = {"done": "Done", "today": "Today"}.get(state, "")
        rows.append(f'<div class="bs-wp {state}"><span class="dd">{DAYS[d][:3]}</span>'
                    f'<span class="tt">{html.escape(label(username, key))}</span><span class="mk">{mark}</span></div>')
    css = ("<style>.bs-wp{display:flex;align-items:center;gap:.8rem;padding:.6rem 0;border-bottom:1px solid rgba(139,92,246,.14)}"
           ".bs-wp .dd{width:2.6rem;font-weight:650;font-size:.9rem;opacity:.7}.bs-wp .tt{flex:1;min-width:0}"
           ".bs-wp .mk{font-size:.8rem;font-weight:650;opacity:.75}.bs-wp.today .dd,.bs-wp.today .mk{color:var(--bs-accent-ink);opacity:1}"
           ".bs-wp.done .mk{color:#16A34A;opacity:1}.bs-wp.done .mk::before{content:'\\2713  '}.bs-wp.past{opacity:.6}</style>")
    return css + "<div>" + "".join(rows) + "</div>"
