"""Skill goals: ladders of progressively harder steps, and when to move up.

Plain rules, no AI. Level-up rule: hit the target on every set in two practices
in a row. Two (not one) so a lucky day doesn't push you onto a step you can't
hold yet. If you miss, you simply repeat the step; nothing is ever lost.
"""
import json
from functools import lru_cache
from pathlib import Path

LADDERS_PATH = Path(__file__).resolve().parent / "progressions.json"
CLEARS_NEEDED = 2


@lru_cache(maxsize=1)
def ladders():
    """{ladder_id: ladder dict}. Bundled with the app, so there is nothing to fetch or maintain."""
    data = json.loads(LADDERS_PATH.read_text())
    return {l["id"]: l for l in data["ladders"]}


def all_ladders(custom=None):
    """Built-in ladders plus the person's own (custom ones carry "custom": True)."""
    return {**ladders(), **(custom or {})}


def target_text(step):
    unit = "s hold" if step.get("kind") == "hold" else " reps"
    side = " per side" if step.get("per_side") else ""
    return f"{step['sets']} × {step['target']}{unit}{side}"


def new_state(step_index=0, today=None):
    return {"step": step_index, "streak": 0, "done": False, "started": today}


def ways(step):
    """Every way to clear a step: the step itself, then any alternatives at the same level (step["options"]).
    Hitting the target of whichever way you did counts toward moving up."""
    return [step] + [o for o in (step.get("options") or []) if o.get("name")]


def evaluate(step, results):
    """results: one number per set (reps or seconds). Returns whether the target was hit."""
    hit = len(results) >= step["sets"] and all(r >= step["target"] for r in results[: step["sets"]])
    return {"hit": hit, "best": max(results) if results else 0, "total": sum(results)}


def advance(state, hit, n_steps):
    """Apply one practice. Returns (new_state, event) where event is one of:
    'miss' | 'clear' (first clear, one more to go) | 'level_up' | 'complete'."""
    s = dict(state)
    if not hit:
        s["streak"] = 0
        return s, "miss"
    s["streak"] = s.get("streak", 0) + 1
    if s["streak"] < CLEARS_NEEDED:
        return s, "clear"
    s["streak"] = 0
    if s["step"] >= n_steps - 1:
        s["done"] = True
        return s, "complete"
    s["step"] += 1
    return s, "level_up"
