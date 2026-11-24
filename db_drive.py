"""Storage in the PERSON'S OWN Google Drive: nothing for you to host, back up or manage.

Everything one person has (profile, lifts, workouts, routines, settings) lives in a
single small JSON file, `bodysync.json`, in their Drive's private "app data" folder.
Only this app can see that folder; the person can delete it any time. The sign-in is
Streamlit's built-in "Sign in with Google" with the `drive.appdata` scope (Google
classes it as non-sensitive). See DEPLOY.md for the one-time Google setup.

How it behaves:
* The file is loaded once per session and kept in memory, so clicks stay instant.
* Every change marks the data "dirty"; `flush()` (called once at the end of each
  page run) uploads it once, however many changes happened in that run.
* If the Google token has expired, `DriveAuthError` is raised and the app asks the
  person to reconnect. Nothing is lost: the unsaved data stays in the session.

This has been tested against a simulated Drive; it has not been exercised against
the real Google API.
"""
import json

import requests
import streamlit as st

FILE_NAME = "bodysync.json"
API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3"
KEY = "_drive"


class DriveAuthError(Exception):
    """The Google connection is missing or expired: ask the person to sign in again."""


class DriveError(Exception):
    pass


# --- talking to Google ---------------------------------------------------------------------
def _session():
    return st.session_state


def _token():
    try:
        return st.user.tokens["access"]
    except Exception as e:
        raise DriveAuthError("No Google access token. Please sign in again.") from e


def _req(method, url, headers=None, **kw):
    r = requests.request(method, url, headers={"Authorization": f"Bearer {_token()}", **(headers or {})}, timeout=20, **kw)
    if r.status_code in (401, 403):
        raise DriveAuthError("Your Google connection expired. Please sign in again.")
    if r.status_code >= 400:
        raise DriveError(f"Google Drive answered {r.status_code}")
    return r


def _blank():
    return {"v": 1, "profile": None, "saved": [], "routines": [], "lifts": {}, "sets": [], "prefs": {}}


def _load():
    r = _req("GET", f"{API}/files", params={"spaces": "appDataFolder", "q": f"name='{FILE_NAME}'", "fields": "files(id)"})
    files = r.json().get("files", [])
    if not files:
        return {"id": None, "doc": _blank(), "dirty": False}
    fid = files[0]["id"]
    doc = _req("GET", f"{API}/files/{fid}", params={"alt": "media"}).json()
    return {"id": fid, "doc": {**_blank(), **doc}, "dirty": False}


def _state():
    s = _session().get(KEY)
    if s is None:
        s = _load()
        _session()[KEY] = s
    return s


def _doc():
    return _state()["doc"]


def _touch():
    _state()["dirty"] = True


def flush():
    """Upload the data if anything changed in this run. Safe to call every run."""
    s = _session().get(KEY)
    if not s or not s["dirty"]:
        return
    body = json.dumps(s["doc"])
    if s["id"]:
        _req("PATCH", f"{UPLOAD}/files/{s['id']}", params={"uploadType": "media"}, data=body.encode(),
             headers={"Content-Type": "application/json"})
    else:
        meta = json.dumps({"name": FILE_NAME, "parents": ["appDataFolder"]})
        b = "bodysyncboundary"
        payload = (f"--{b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
                   f"--{b}\r\nContent-Type: application/json\r\n\r\n{body}\r\n--{b}--").encode()
        r = _req("POST", f"{UPLOAD}/files", params={"uploadType": "multipart", "fields": "id"}, data=payload,
                 headers={"Content-Type": f"multipart/related; boundary={b}"})
        s["id"] = r.json()["id"]
    s["dirty"] = False


def has_unsaved():
    s = _session().get(KEY)
    return bool(s and s["dirty"])


# --- accounts: Google handles these, so there is nothing to do ------------------------------------
def create_user(username, password):
    return False, "Accounts are handled by Google sign-in."


def verify_user(username, password):
    return False


# --- profile ---------------------------------------------------------------------------------
def get_profile(username):
    p = _doc()["profile"]
    return {"username": username, **p} if p else None


def save_profile(username, age, weight, height, fitness_level, health_condition):
    _doc()["profile"] = {"age": age, "weight": weight, "height": height,
                         "fitness_level": fitness_level, "health_condition": health_condition}
    _touch()


# --- saved workouts -------------------------------------------------------------------------------
def list_saved_workouts(username):
    return sorted(_doc()["saved"])


def is_workout_saved(username, workout_name):
    return workout_name in _doc()["saved"]


def save_workout(username, workout_name):
    if workout_name not in _doc()["saved"]:
        _doc()["saved"].append(workout_name)
        _touch()


def unsave_workout(username, workout_name):
    if workout_name in _doc()["saved"]:
        _doc()["saved"].remove(workout_name)
        _touch()


# --- routines ---------------------------------------------------------------------------------
def add_routine_item(username, routine_name, workout_name, sets, reps, minutes):
    _doc()["routines"].append({"routine_name": routine_name, "workout_name": workout_name,
                               "sets": sets, "reps": reps, "minutes": minutes})
    _touch()


def list_routines(username):
    return sorted({r["routine_name"] for r in _doc()["routines"]})


def get_routine(username, routine_name):
    return [{k: r[k] for k in ("workout_name", "sets", "reps", "minutes")}
            for r in _doc()["routines"] if r["routine_name"] == routine_name]


def delete_routine(username, routine_name):
    _doc()["routines"] = [r for r in _doc()["routines"] if r["routine_name"] != routine_name]
    _touch()


# --- baseline lifts --------------------------------------------------------------------------
def upsert_lift(username, exercise, day_type, pr_weight, pr_reps, rep_low=8, rep_high=12, sets=3):
    _doc()["lifts"][exercise] = {"exercise": exercise, "day_type": day_type, "pr_weight": pr_weight,
                                 "pr_reps": pr_reps, "rep_low": rep_low, "rep_high": rep_high, "sets": sets}
    _touch()


def list_lifts(username):
    return sorted(_doc()["lifts"].values(), key=lambda l: l["exercise"])


def delete_lift(username, exercise):
    if _doc()["lifts"].pop(exercise, None) is not None:
        _touch()


# --- logged sets -----------------------------------------------------------------------------
def log_sets(username, session_id, performed_at, day_type, rows):
    for r in rows:
        _doc()["sets"].append({
            "session_id": session_id, "performed_at": performed_at, "day_type": day_type,
            "exercise": r["exercise"], "set_no": r["set_no"], "weight": r["weight"], "reps": r["reps"],
            "is_pr": bool(r.get("is_pr")),
        })
    _touch()


def list_sets(username, exercise=None):
    rows = [s for s in _doc()["sets"] if exercise is None or s["exercise"] == exercise]
    return sorted(rows, key=lambda s: s["performed_at"])  # stable: keeps set order within a session


# --- preferences ---------------------------------------------------------------------------------
def get_pref(username, key, default=None):
    return _doc()["prefs"].get(key, default)


def set_pref(username, key, value):
    _doc()["prefs"][key] = str(value)
    _touch()
