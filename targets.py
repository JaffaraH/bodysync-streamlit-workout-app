"""What each move works and why it's there, the 'for your goal' note on a curated workout, and the honest
'feeling stuck?' check on Progress. Plain rules (no Streamlit), so tests can run them.

Data: move_targets.json (areas and jobs per move, goal notes). Every research id it names must be verified in
research.json; research.do() returns '' for anything that isn't, so an unverified line is never shown.
"""
import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).parent / "move_targets.json"
STUCK_DAYS = 28  # about 4 weeks: long enough that no new record means something, short enough to still help
NOT_LIFTING = ("stretch", "cardio", "skill")


@lru_cache(maxsize=1)
def data():
    return json.loads(PATH.read_text())


def move(name):
    """{'area', 'job', 'research'?} for a move, or None for a move we haven't described (your own, most library ones)."""
    return data()["moves"].get((name or "").replace("Skill: ", ""))


def works(name):
    """'Works: deep core. Keeps your lower back down...' for a list row; '' when the move isn't described."""
    m = move(name)
    return f"Works: {m['area'][:1].lower()}{m['area'][1:]}. {m['job']}" if m else ""


def goal_note(workout):
    """The 'for your goal' note for a curated workout: {'title', 'lines', 'tip', 'research', 'expect'}, or None."""
    g = data()["goals"].get(workout.get("for_goal") or "")
    if not g:
        return None
    return {**g, "tip": workout.get("goal_tip", ""), "expect": data()["expect"]}


def all_research_ids():
    """Every research id this layer can show (tests check each is verified)."""
    d = data()
    ids = {r for m in d["moves"].values() for r in ([m["research"]] if m.get("research") else [])}
    ids |= {r for g in d["goals"].values() for r in g["research"]}
    return ids | set(d["expect"]["research"])


# --- feeling stuck? ----------------------------------------------------------------------------------------
def _day(ts):
    return datetime.fromisoformat(ts).date()


def _top(rows):
    return max((s["weight"] or 0, s["reps"] or 0) for s in rows)


def stuck(sets, today=None):
    """Whether to show 'Feeling stuck?', with the person's own numbers, or None.

    Shown when someone has logged for at least 4 weeks, has lifted in the last 4 weeks (a longer break gets the
    welcome-back note instead), and set no personal record in that time. Returns:
    {'days': lifting days in the last 4 weeks, 'per_week': that / 4,
     'lift': most-done lift (most sessions, then most sets) or None, 'first': (weight, reps) of its first top set in that time, 'last': the latest one, 'moved': last beats first}.
    """
    today = today or date.today()
    lifting = [s for s in sets if s.get("day_type") not in NOT_LIFTING and not s["exercise"].startswith("Walk: ")]
    if not lifting:
        return None
    first = min(_day(s["performed_at"]) for s in sets)
    recent = [s for s in lifting if (today - _day(s["performed_at"])).days < STUCK_DAYS]
    if (today - first).days < STUCK_DAYS or not recent:
        return None
    if any(s.get("is_pr") and (today - _day(s["performed_at"])).days < STUCK_DAYS for s in sets):
        return None  # a new record in the last 4 weeks: not stuck
    days = len({_day(s["performed_at"]) for s in recent})
    by_lift = {}
    for s in recent:
        by_lift.setdefault(s["exercise"], {}).setdefault(s["session_id"], []).append(s)
    lift = max(by_lift, key=lambda n: (len(by_lift[n]), sum(map(len, by_lift[n].values())), n))
    sessions = sorted(by_lift[lift].values(), key=lambda rows: rows[0]["performed_at"])
    a, b = _top(sessions[0]), _top(sessions[-1])
    return {"days": days, "per_week": days / 4, "lift": lift if len(sessions) >= 2 else None,
            "first": a, "last": b, "moved": b > a}
