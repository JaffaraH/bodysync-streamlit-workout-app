"""Per-session cache in front of `db`.

Streamlit reruns the script on every click. With a cloud database (BigQuery)
re-querying each time makes every click feel slow, so we load once, keep the
result in the session, and update it right after each write.
"""
import json

import streamlit as st

import db


def _store():
    return st.session_state.setdefault("_data", {})


def _get(key, loader):
    store = _store()
    if key not in store:
        store[key] = loader()
    return store[key]


def clear():
    st.session_state.pop("_data", None)


# --- profile ----------------------------------------------------------------
def profile(username):
    return _get("profile", lambda: db.get_profile(username))


def save_profile(username, age, weight_lb, height_ft, level, health):
    db.save_profile(username, age, weight_lb, height_ft, level, health)
    _store()["profile"] = {
        "username": username, "age": age, "weight": weight_lb, "height": height_ft,
        "fitness_level": level, "health_condition": health,
    }


def profile_summary(username):
    p = profile(username)
    if not p:
        return "No profile saved (give general advice)."
    parts = []
    if p.get("age"):
        parts.append(f"age {p['age']}")
    if p.get("weight"):
        parts.append(f"weight {p['weight']:.0f} lb")
    if p.get("height"):
        ft = float(p["height"])
        parts.append(f"height {int(ft)} ft {round((ft - int(ft)) * 12)} in")
    parts.append(f"fitness level {p.get('fitness_level') or 'unspecified'}")
    parts.append(f"health conditions: {p.get('health_condition') or 'none'}")
    return ", ".join(parts).capitalize() + "."


# --- saved workouts ---------------------------------------------------------
def saved_workouts(username):
    return _get("saved", lambda: set(db.list_saved_workouts(username)))


def save_workout(username, name):
    db.save_workout(username, name)
    saved_workouts(username).add(name)


def unsave_workout(username, name):
    db.unsave_workout(username, name)
    saved_workouts(username).discard(name)


# --- routines ---------------------------------------------------------------
def routines(username):
    return _get("routines", lambda: list(db.list_routines(username)))


def routine_items(username, name):
    return _get(f"routine::{name}", lambda: db.get_routine(username, name))


def add_routine(username, name, exercises, sets, reps, minutes):
    for ex in exercises:
        db.add_routine_item(username, name, ex, sets, reps, minutes)
    store = _store()
    store.pop(f"routine::{name}", None)
    if name not in routines(username):
        routines(username).append(name)
        routines(username).sort()


def delete_routine(username, name):
    db.delete_routine(username, name)
    _store().pop(f"routine::{name}", None)
    if name in routines(username):
        routines(username).remove(name)


# --- units (weights are always stored in lb) ----------------------------------
def unit(username):
    return _get("unit", lambda: db.get_pref(username, "unit", "lb"))


def set_unit(username, value):
    db.set_pref(username, "unit", value)
    _store()["unit"] = value


# --- baseline lifts -----------------------------------------------------------
def lifts(username):
    return _get("lifts", lambda: db.list_lifts(username))


def upsert_lift(username, exercise, day_type, pr_weight, pr_reps, rep_low=8, rep_high=12, sets=3):
    db.upsert_lift(username, exercise, day_type, pr_weight, pr_reps, rep_low, rep_high, sets)
    _store().pop("lifts", None)


def delete_lift(username, exercise):
    db.delete_lift(username, exercise)
    _store().pop("lifts", None)


# --- logged sets --------------------------------------------------------------
def all_sets(username):
    """Every logged set, minus workouts you removed (hidden, not deleted, so Undo works on every backend)."""
    hidden = set(settings(username).get("hidden_sessions") or [])
    rows = _get("sets", lambda: db.list_sets(username))
    return [r for r in rows if r["session_id"] not in hidden] if hidden else rows


def hide_session(username, session_id, hide=True):
    hidden = set(settings(username).get("hidden_sessions") or [])
    hidden = hidden | {session_id} if hide else hidden - {session_id}
    save_settings(username, hidden_sessions=sorted(hidden))


def log_sets(username, session_id, performed_at, day_type, rows):
    db.log_sets(username, session_id, performed_at, day_type, rows)
    _store().pop("sets", None)


# --- skill goals (stored as JSON in the existing preferences table: no schema change) ----
def skills(username):
    def load():
        try:
            return json.loads(db.get_pref(username, "skills", "{}"))
        except ValueError:
            return {}
    return _get("skills", load)


def save_skills(username, data):
    db.set_pref(username, "skills", json.dumps(data))
    _store()["skills"] = data


# --- personal settings: what you're here for, weekly goal, how exercises felt -----------
# One small JSON blob in the existing preferences table (no schema change on any backend).
def settings(username):
    def load():
        try:
            return json.loads(db.get_pref(username, "settings", "{}"))
        except ValueError:
            return {}
    return _get("settings", load)


def save_settings(username, **changes):
    merged = {**settings(username), **changes}
    db.set_pref(username, "settings", json.dumps(merged))
    _store()["settings"] = merged


# --- skills people create themselves (steps, drills, own pictures), as JSON in preferences ------
def custom_skills(username):
    def load():
        try:
            return json.loads(db.get_pref(username, "custom_skills", "{}"))
        except ValueError:
            return {}
    return _get("custom_skills", load)


def save_custom_skills(username, data):
    db.set_pref(username, "custom_skills", json.dumps(data))
    _store()["custom_skills"] = data


# --- a workout in progress, saved after every set so a sleeping phone or a reload loses nothing ----------
def save_live(username, sess):
    data = {**sess, "notified": sorted(sess.get("notified") or [])}
    db.set_pref(username, "live_session", json.dumps(data, default=str))


def load_live(username):
    try:
        data = json.loads(db.get_pref(username, "live_session", "") or "null")
    except ValueError:
        return None
    if not data or not data.get("items"):
        return None
    data["notified"] = set(data.get("notified") or [])
    data.pop("rest", None)  # a rest timer from before the break has no meaning now
    return data


def clear_live(username):
    db.set_pref(username, "live_session", "")
