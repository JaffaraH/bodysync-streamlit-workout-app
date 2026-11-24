"""Training logic for BodySync: progressive overload, returning from a break,
personal records and picking today's lineup.

Everything here is plain rules (no AI, no network), so it is instant, free and
works for everyone. Weights are stored in pounds; `unit` ("lb" or "kg") only
affects rounding steps and display.

Sources for the rules (coaching consensus, not clinical trials):
* Double progression: add reps within a range, then add weight and start the
  range again (the approach used by Gravl, Alpha Progression and others).
* After a break: roughly 75% of previous loads after a few weeks off, down to
  ~50% after several months, with a bit less volume (PureGym, Breaking Muscle).
"""
from collections import defaultdict
from datetime import date, datetime

LB_PER_KG = 2.20462
LOWER = {"quadriceps", "hamstrings", "glutes", "calves", "adductors", "abductors", "lower back"}
CORE = {"abdominals"}
DAY_LABELS = {"upper": "Upper body", "lower": "Lower body", "full": "Full body", "core": "Core", "skill": "Skill practice",
              "cardio": "Walk", "stretch": "Stretch"}
EPS = 0.01


# --- units ----------------------------------------------------------------------
def to_unit(lb, unit):
    return lb / LB_PER_KG if unit == "kg" else lb


def from_unit(value, unit):
    return value * LB_PER_KG if unit == "kg" else value


def fmt_weight(lb, unit="lb"):
    if lb is None:
        return "-"
    v = round(to_unit(lb, unit), 1)
    return f"{v:g} {unit}"


def step(day_type, unit):
    """Smallest jump when adding weight: 5 lb upper / 10 lb lower (2.5 / 5 kg)."""
    big = day_type == "lower"
    return (5 if big else 2.5) if unit == "kg" else (10 if big else 5)


def jump_for(top_lb, day_type, unit):
    """How much to add: ACSM 2009 advises 2-10% (research.json: progression-top-of-range). The usual step
    (5 lb upper / 10 lb lower) is used when it stays near 10%; light weights get the half step instead."""
    full = step(day_type, unit)
    return full if to_unit(top_lb, unit) * 0.10 >= full * 0.75 else full / 2


def round_to(lb, unit, jump):
    """Round a weight (lb) to the nearest `jump` in the user's unit; returns lb."""
    return from_unit(round(to_unit(lb, unit) / jump) * jump, unit)


# --- exercise helpers -----------------------------------------------------------
def guess_day_type(exercise):
    muscles = set(exercise.get("primaryMuscles") or [])
    if muscles & LOWER:
        return "lower"
    if muscles & CORE:
        return "core"
    return "upper"


def e1rm(weight, reps):
    """Epley estimate of a one-rep max."""
    return weight if reps <= 1 else weight * (1 + reps / 30)


MILESTONES = {"lb": [100, 135, 185, 225, 275, 315, 365, 405, 455, 495], "kg": [40, 60, 80, 100, 120, 140, 160, 180, 200]}


def milestone_crossed(before_lb, after_lb, unit="lb"):
    """'First time over 225 lb' when a lift crosses a round number for the first time, else None.
    No milestone is claimed for a lift that had no previous best."""
    if not before_lb:
        return None
    a, b = to_unit(before_lb, unit), to_unit(after_lb, unit)
    crossed = [m for m in MILESTONES[unit] if a < m <= b + 1e-6]
    return f"First time over {max(crossed)} {unit}" if crossed else None


# --- history ---------------------------------------------------------------------
def _day(performed_at):
    return datetime.fromisoformat(performed_at).date()


def group_sessions(sets):
    """Logged sets -> sessions, newest first: {session_id, performed_at, day_type, sets}."""
    by = defaultdict(list)
    for s in sets:
        by[s["session_id"]].append(s)
    out = [
        {"session_id": sid, "performed_at": rows[0]["performed_at"], "day_type": rows[0]["day_type"], "sets": rows}
        for sid, rows in by.items()
    ]
    return sorted(out, key=lambda x: x["performed_at"], reverse=True)


def lift_history(sets, exercise):
    """Sessions (newest first) with only this exercise's sets."""
    out = []
    for sess in group_sessions(sets):
        rows = [s for s in sess["sets"] if s["exercise"] == exercise]
        if rows:
            out.append({**sess, "sets": rows})
    return out


def days_since(performed_at, today=None):
    today = today or date.today()
    return (today - _day(performed_at)).days


def break_factor(days_off):
    """Share of previous working weight to start with after `days_off` days away."""
    if days_off < 14:
        return 1.0
    if days_off < 28:
        return 0.9
    if days_off < 56:
        return 0.75
    if days_off < 112:
        return 0.6
    return 0.5


def break_label(days_off):
    if days_off < 14:
        return "this week" if days_off < 7 else "a week or so ago"
    weeks = days_off // 7
    if weeks < 9:
        return f"about {weeks} weeks ago"
    months = round(days_off / 30)
    return f"about {months} months ago"


# --- progressive overload ------------------------------------------------------
def suggest(lift, history, days_off, unit="lb", feel=None):
    """What to do for one lift today. `feel` is how the last session felt: easy | right | hard | pain.

    Returns {"weight" (lb or None), "reps" (target per set), "sets", "tag", "reason"}.
    """
    low, high, n_sets = lift.get("rep_low") or 8, lift.get("rep_high") or 12, lift.get("sets") or 3
    jump = step(lift["day_type"], unit)
    factor = break_factor(days_off)
    ease_sets = max(2, n_sets - 1) if days_off >= 28 else n_sets

    if not history:
        pr_w, pr_r = lift.get("pr_weight"), lift.get("pr_reps")
        if not pr_w:
            return {"weight": None, "reps": low, "sets": n_sets, "tag": "start",
                    "reason": "First time: pick a weight you could lift about 10 times, then log it."}
        base = e1rm(pr_w, pr_r or 1) * 0.75 * factor  # 75% of est. max is roughly a 10-rep weight
        note = f" (eased to {int(factor * 100)}% after time off)" if factor < 1 else ""
        return {"weight": round_to(base, unit, jump), "reps": low, "sets": ease_sets, "tag": "start",
                "reason": f"No logs yet, so we started from 75% of your estimated max{note}. Adjust if it feels off."}

    last = history[0]["sets"]
    top = max(s["weight"] for s in last)
    at_top = [s for s in last if abs(s["weight"] - top) < EPS]
    bodyweight = top < EPS  # push-ups, pull-ups...: progress with reps, then a harder version, never "add 5 lb"
    fmt_last = (", ".join(str(s["reps"]) for s in at_top) + " reps" if bodyweight
                else f"{fmt_weight(top, unit)} × " + ", ".join(str(s["reps"]) for s in at_top))

    if feel == "pain":
        return {"weight": round_to(top * 0.8, unit, jump), "reps": low, "sets": n_sets, "tag": "ease",
                "reason": f"Last time {fmt_last}, and you said something hurt. Go lighter (80%), slow down and check your "
                          f"form. If the pain continues, stop and get it looked at."}
    if factor < 1:
        return {"weight": round_to(top * factor, unit, jump), "reps": low, "sets": ease_sets, "tag": "ease",
                "reason": f"Last time {fmt_last}. It's been a while, so ease back in at {int(factor * 100)}% "
                          f"and build up over a few sessions."}
    jump = jump_for(top, lift["day_type"], unit)
    if len(at_top) >= n_sets and all(s["reps"] >= high for s in at_top):
        if bodyweight:
            return {"weight": 0, "reps": high, "sets": n_sets, "tag": "add",
                    "reason": f"Last time {fmt_last}: the top of the range on every set. Ready for a harder version "
                              f"(Change in the lineup, or a skill ladder), or slow the lowering to 3 seconds."}
        if feel == "hard":
            return {"weight": top, "reps": high, "sets": n_sets, "tag": "repeat",
                    "reason": f"Last time {fmt_last}: you hit the top of the range, but it felt hard. "
                              f"Hold this weight one more session before adding."}
        twice = False  # ACSM: add load after two sessions in a row above target (or one that felt easy)
        if len(history) > 1:
            prev = [x for x in history[1]["sets"] if abs(x["weight"] - top) < EPS]
            twice = len(prev) >= n_sets and all(x["reps"] >= high for x in prev)
        if twice or feel == "easy":
            return {"weight": top + from_unit(jump, unit), "reps": low, "sets": n_sets, "tag": "add",
                    "reason": f"Last time {fmt_last}: the top of the range on every set"
                              + (", two sessions in a row" if twice else ", and it felt easy") + f". Add {jump:g} {unit}!"}
        return {"weight": top, "reps": high, "sets": n_sets, "tag": "reps",
                "reason": f"Last time {fmt_last}: the top of the range on every set. "
                          f"Do it once more and the weight goes up next time."}
    if all(s["reps"] >= low for s in at_top):
        if feel == "easy" and len(at_top) >= n_sets and not bodyweight:
            return {"weight": top + from_unit(jump, unit), "reps": low, "sets": n_sets, "tag": "add",
                    "reason": f"Last time {fmt_last}, and you said it felt easy. Add {jump:g} {unit}."}
        want = min(high, min(s["reps"] for s in at_top) + 1)
        return {"weight": top, "reps": want, "sets": n_sets, "tag": "reps",
                "reason": f"Last time {fmt_last}. Same weight, aim for {want} reps each set."}
    # missed the bottom of the range
    if len(history) > 1:
        prev = history[1]["sets"]
        prev_top = max(s["weight"] for s in prev)
        if abs(prev_top - top) < EPS and any(s["reps"] < low for s in prev if abs(s["weight"] - top) < EPS):
            return {"weight": round_to(top * 0.9, unit, jump), "reps": low, "sets": n_sets, "tag": "deload",
                    "reason": f"Two tough sessions in a row at {fmt_weight(top, unit)}. "
                              f"Drop 10% this time and build back up. That's normal."}
    return {"weight": top, "reps": low, "sets": n_sets, "tag": "repeat",
            "reason": f"Last time {fmt_last}. Repeat it and aim for {low}+ reps on every set."}


# --- personal records -------------------------------------------------------------
class PRTracker:
    """Walks through sets in order and says which ones beat the previous best.

    A PR is either a heavier weight than ever before ("weight") or more reps at a
    weight you've lifted before ("reps"). If there is no history and no baseline
    at all, nothing is called a PR: that first set simply sets your starting bar.
    """

    def __init__(self, previous_sets, baseline_weight=None, baseline_reps=None):
        self.best_w = 0.0
        self.reps_at = {}
        self.has_bar = False
        for s in previous_sets:
            self._add(s["weight"], s["reps"])
        if baseline_weight:
            self._add(baseline_weight, baseline_reps or 1)

    def _add(self, w, r):
        self.has_bar = True
        self.best_w = max(self.best_w, w)
        key = round(w, 1)
        self.reps_at[key] = max(self.reps_at.get(key, 0), r)

    def add(self, weight, reps):
        """Record a set; returns "weight", "reps" or None."""
        kind = None
        if self.has_bar and weight >= 0 and reps > 0:  # weight 0 = bodyweight lifts (rep PRs only)
            if weight > self.best_w + EPS:
                kind = "weight"
            elif reps > self.reps_at.get(round(weight, 1), 0) and round(weight, 1) in self.reps_at:
                kind = "reps"
        self._add(weight, reps)
        return kind


def find_prs(previous_sets, new_sets, baseline_weight=None, baseline_reps=None):
    """new_sets: [{"weight","reps"}] in order. Returns (flags per set, best PR message or None)."""
    tracker = PRTracker(previous_sets, baseline_weight, baseline_reps)
    flags = [tracker.add(s["weight"], s["reps"]) for s in new_sets]
    best = None
    for s, kind in zip(new_sets, flags):
        if kind and (best is None or s["weight"] > best["weight"] or (s["weight"] == best["weight"] and s["reps"] > best["reps"])):
            best = {"kind": kind, "weight": s["weight"], "reps": s["reps"]}
    return flags, best


# --- choosing today's workout --------------------------------------------------------
def suggest_split(last_day_type, has_upper=True, has_lower=True):
    """Alternate upper/lower; otherwise full body."""
    if last_day_type == "upper" and has_lower:
        return "lower"
    if last_day_type == "lower" and has_upper:
        return "upper"
    if has_upper and has_lower:
        return "full"
    return "upper" if has_upper else "lower"


def strength_sets(sets):
    """Only the lifting sets (skill practice and walks are logged in the same table)."""
    return [s for s in sets if s.get("day_type") not in ("skill", "cardio", "stretch")]


def last_trained(sets):
    """{exercise: date of last log}."""
    out = {}
    for s in sets:
        out[s["exercise"]] = _day(s["performed_at"])
    return out


def pick_lineup(lifts, day, sets, n=4):
    """Pick up to n lifts for the day, favouring the ones trained longest ago."""
    seen = last_trained(sets)
    never = date.min

    def order(group):
        # least recently trained first; ties favour lifts the user entered a PR for
        return sorted(group, key=lambda l: (seen.get(l["exercise"], never), l.get("pr_weight") is None, l["exercise"]))

    upper = order([l for l in lifts if l["day_type"] == "upper"])
    lower = order([l for l in lifts if l["day_type"] == "lower"])
    core = order([l for l in lifts if l["day_type"] == "core"])
    if day == "upper":
        pool = upper
    elif day == "lower":
        pool = lower
    else:  # full body: alternate lower / upper so both are covered
        pool = [x for pair in zip(lower, upper) for x in pair]
        pool += lower[len(upper):] + upper[len(lower):]
    pool = pool + core if len(pool) < n else pool
    return [l["exercise"] for l in pool[:n]]


def streak_summary(sets, today=None):
    """(workouts this week, days since last workout or None)."""
    today = today or date.today()
    sessions = group_sessions(sets)
    if not sessions:
        return 0, None
    monday = today.toordinal() - today.weekday()
    this_week = sum(1 for s in sessions if _day(s["performed_at"]).toordinal() >= monday)
    return this_week, days_since(sessions[0]["performed_at"], today)


def week_dots(sets, today=None):
    """Seven booleans Mon..Sun: did you train that day this week?"""
    today = today or date.today()
    monday = today.toordinal() - today.weekday()
    trained = {_day(s["performed_at"]).toordinal() for s in sets}
    return [(monday + i) in trained for i in range(7)]


# --- saying "how much" in the right unit, everywhere ---------------------------------------------
@__import__("functools").lru_cache(maxsize=1)
def hold_names():
    """Exercises done as timed holds (marked "hold" in curated_workouts.json): their reps are seconds."""
    import json
    from pathlib import Path as _P
    try:
        data = json.loads((_P(__file__).parent / "curated_workouts.json").read_text())["workouts"]
    except (OSError, ValueError, KeyError):
        return set()
    return {e[0] for w in data for e in w["exercises"] if e[4:] == ["hold"]}


# Exercises people create themselves can be holds too. Their names live in that person's session, which this
# module can't see (it has no Streamlit in it), so exercise_data plugs in a function that returns them.
EXTRA_HOLDS = lambda: set()  # noqa: E731


def kind_of(exercise, day_type=None):
    """'minutes' for walks, 'hold' for timed holds, else 'reps' (weights are shown when there are any)."""
    if day_type == "cardio" or exercise.startswith("Walk: "):
        return "minutes"
    return "hold" if exercise in hold_names() or exercise in EXTRA_HOLDS() else "reps"


def amount(weight_lb, reps, unit, kind="reps"):
    """One way to say how much: '50 seconds', '30 minutes', '12 reps', '135 lb × 8' (lb or kg)."""
    reps = int(reps)
    if kind == "hold":
        return f"{reps} second{'s' if reps != 1 else ''}"
    if kind == "minutes":
        return f"{reps} minute{'s' if reps != 1 else ''}"
    if not weight_lb:
        return f"{reps} rep{'s' if reps != 1 else ''}"
    return f"{fmt_weight(weight_lb, unit)} × {reps}"


# --- swap: other exercises for the same muscles ------------------------------------------------------
LEVEL_RANK = {"beginner": 0, "intermediate": 1, "expert": 2}
LIFT_CATEGORIES = {"strength", "powerlifting", "olympic weightlifting", "strongman", "plyometrics"}


HOLD_WORDS = ("plank", "bridge", "hold", "dead hang", "flexed-arm hang", "wall sit", "l-sit", "hollow")


def alternatives(name, exercises, n=3, avoid=(), hold=False):
    """Up to n exercises that train the same main muscles as `name`, best first: same primary muscles, then the
    same movement type (compound or isolation), similar equipment, and the same level or easier. Only ones with a
    picture. Stretches swap only for stretches; lifts only for lifts."""
    by = {e["name"]: e for e in exercises}
    me = by.get(name)
    if not me:
        return []
    prim = set(me.get("primaryMuscles") or [])
    stretch = me.get("category") == "stretching"
    lvl = LEVEL_RANK.get(me.get("level"), 1)
    scored = []
    for e in exercises:
        if e["name"] == name or e["name"] in avoid or not e.get("images"):
            continue
        if (e.get("category") == "stretching") != stretch or (not stretch and e.get("category") not in LIFT_CATEGORIES):
            continue
        if (e.get("category") == "plyometrics") != (me.get("category") == "plyometrics"):
            continue  # a jump is not a swap for a squat, and the other way round
        low = e["name"].lower()
        if any(w in low and w not in name.lower() for w in ("isometric", "jump", "hanging")):
            continue  # a jump or a hanging move is a different job, not a swap
        if hold and not (e["name"] in hold_names() or any(w in e["name"].lower() for w in HOLD_WORDS)):
            continue  # a hold swaps for another hold
        no_kit = (me.get("equipment") or "body only") == "body only"
        if no_kit and (e.get("equipment") or "body only") not in ("body only",):
            continue  # training without equipment: only suggest moves that need none
        p = set(e.get("primaryMuscles") or [])
        if not p & prim:
            continue
        score = 3 * len(p & prim) - 2 * len(p - prim)
        score += 2 if e.get("mechanic") == me.get("mechanic") else 0
        score += 2 if e.get("force") == me.get("force") else 0  # push for push, pull for pull, hold for hold
        score += 1 if e.get("category") == me.get("category") else 0
        score += 1 if e.get("equipment") == me.get("equipment") else 0
        score += 1 if LEVEL_RANK.get(e.get("level"), 1) <= lvl else -2
        scored.append((-score, e["name"]))
    picked, stems = [], set()
    for _, nm in sorted(scored):
        stem = " ".join(nm.lower().replace("-", " ").split()[:2])  # skip near-duplicates ("Barbell Squat To A Bench")
        if stem in stems:
            continue
        stems.add(stem)
        picked.append(nm)
        if len(picked) == n:
            break
    return picked
