"""Local SQLite backend (the default). Same interface as db_bigquery.py."""
import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS profiles (
    username TEXT PRIMARY KEY,
    age INTEGER,
    weight REAL,
    height REAL,
    fitness_level TEXT,
    health_condition TEXT
);
CREATE TABLE IF NOT EXISTS saved_workouts (
    username TEXT NOT NULL,
    workout_name TEXT NOT NULL,
    PRIMARY KEY (username, workout_name)
);
CREATE TABLE IF NOT EXISTS routines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    routine_name TEXT NOT NULL,
    workout_name TEXT NOT NULL,
    sets INTEGER,
    reps INTEGER,
    minutes REAL
);
CREATE TABLE IF NOT EXISTS lifts (
    username TEXT NOT NULL,
    exercise TEXT NOT NULL,
    day_type TEXT NOT NULL,
    pr_weight REAL,
    pr_reps INTEGER,
    rep_low INTEGER DEFAULT 8,
    rep_high INTEGER DEFAULT 12,
    sets INTEGER DEFAULT 3,
    PRIMARY KEY (username, exercise)
);
CREATE TABLE IF NOT EXISTS workout_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    session_id TEXT NOT NULL,
    performed_at TEXT NOT NULL,
    day_type TEXT,
    exercise TEXT NOT NULL,
    set_no INTEGER,
    weight REAL,
    reps INTEGER,
    is_pr INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sets_user ON workout_sets (username, performed_at);
CREATE TABLE IF NOT EXISTS user_prefs (
    username TEXT NOT NULL,
    pref_key TEXT NOT NULL,
    pref_value TEXT,
    PRIMARY KEY (username, pref_key)
);
"""

_ready = False


@contextmanager
def _connect():
    global _ready
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if not _ready:  # create tables once per process, not on every query
            conn.executescript(SCHEMA)
            _ready = True
        yield conn
        conn.commit()
    finally:
        conn.close()


# --- accounts ---------------------------------------------------------------
def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


def create_user(username: str, password: str):
    """Returns (ok, message)."""
    username = username.strip()
    if not username or not password:
        return False, "Username and password are required."
    salt = os.urandom(16)
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?)",
                (username, salt.hex(), _hash(password, salt)),
            )
    except sqlite3.IntegrityError:
        return False, "That username is already taken."
    return True, "Account created."


def verify_user(username: str, password: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT salt, password_hash FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
    if not row:
        return False
    return hmac.compare_digest(_hash(password, bytes.fromhex(row["salt"])), row["password_hash"])


# --- profile ----------------------------------------------------------------
def get_profile(username: str):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def save_profile(username, age, weight, height, fitness_level, health_condition):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO profiles (username, age, weight, height, fitness_level, health_condition)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(username) DO UPDATE SET
                 age=excluded.age, weight=excluded.weight, height=excluded.height,
                 fitness_level=excluded.fitness_level, health_condition=excluded.health_condition""",
            (username, age, weight, height, fitness_level, health_condition),
        )


# --- saved workouts ---------------------------------------------------------
def is_workout_saved(username, workout_name) -> bool:
    return workout_name in set(list_saved_workouts(username))


def save_workout(username, workout_name):
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO saved_workouts (username, workout_name) VALUES (?, ?)",
            (username, workout_name),
        )


def unsave_workout(username, workout_name):
    with _connect() as conn:
        conn.execute(
            "DELETE FROM saved_workouts WHERE username = ? AND workout_name = ?",
            (username, workout_name),
        )


def list_saved_workouts(username):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT workout_name FROM saved_workouts WHERE username = ? ORDER BY workout_name",
            (username,),
        ).fetchall()
    return [r["workout_name"] for r in rows]


# --- routines ---------------------------------------------------------------
def add_routine_item(username, routine_name, workout_name, sets, reps, minutes):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO routines (username, routine_name, workout_name, sets, reps, minutes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, routine_name, workout_name, sets, reps, minutes),
        )


def list_routines(username):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT routine_name FROM routines WHERE username = ? ORDER BY routine_name",
            (username,),
        ).fetchall()
    return [r["routine_name"] for r in rows]


def get_routine(username, routine_name):
    with _connect() as conn:
        rows = conn.execute(
            """SELECT workout_name, sets, reps, minutes FROM routines
               WHERE username = ? AND routine_name = ? ORDER BY id""",
            (username, routine_name),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_routine(username, routine_name):
    with _connect() as conn:
        conn.execute(
            "DELETE FROM routines WHERE username = ? AND routine_name = ?",
            (username, routine_name),
        )


# --- baseline lifts (the user's "go-to" lifts and personal records) ----------
def upsert_lift(username, exercise, day_type, pr_weight, pr_reps, rep_low=8, rep_high=12, sets=3):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO lifts (username, exercise, day_type, pr_weight, pr_reps, rep_low, rep_high, sets)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(username, exercise) DO UPDATE SET
                 day_type=excluded.day_type, pr_weight=excluded.pr_weight, pr_reps=excluded.pr_reps,
                 rep_low=excluded.rep_low, rep_high=excluded.rep_high, sets=excluded.sets""",
            (username, exercise, day_type, pr_weight, pr_reps, rep_low, rep_high, sets),
        )


def list_lifts(username):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT exercise, day_type, pr_weight, pr_reps, rep_low, rep_high, sets "
            "FROM lifts WHERE username = ? ORDER BY exercise",
            (username,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_lift(username, exercise):
    with _connect() as conn:
        conn.execute("DELETE FROM lifts WHERE username = ? AND exercise = ?", (username, exercise))


# --- logged sets (every set the user completed) ------------------------------
def log_sets(username, session_id, performed_at, day_type, rows):
    """rows: [{exercise, set_no, weight, reps, is_pr}]. Weights are stored in lb."""
    with _connect() as conn:
        conn.executemany(
            """INSERT INTO workout_sets
               (username, session_id, performed_at, day_type, exercise, set_no, weight, reps, is_pr)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (username, session_id, performed_at, day_type, r["exercise"], r["set_no"],
                 r["weight"], r["reps"], 1 if r.get("is_pr") else 0)
                for r in rows
            ],
        )


def list_sets(username, exercise=None):
    """All logged sets (oldest first), optionally for one exercise."""
    sql = ("SELECT session_id, performed_at, day_type, exercise, set_no, weight, reps, is_pr "
           "FROM workout_sets WHERE username = ?")
    args = [username]
    if exercise:
        sql += " AND exercise = ?"
        args.append(exercise)
    with _connect() as conn:
        rows = conn.execute(sql + " ORDER BY performed_at, id", args).fetchall()
    return [{**dict(r), "is_pr": bool(r["is_pr"])} for r in rows]


# --- small per-user preferences (e.g. kg/lb) ----------------------------------
def get_pref(username, key, default=None):
    with _connect() as conn:
        row = conn.execute(
            "SELECT pref_value FROM user_prefs WHERE username = ? AND pref_key = ?", (username, key)
        ).fetchone()
    return row["pref_value"] if row else default


def set_pref(username, key, value):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO user_prefs (username, pref_key, pref_value) VALUES (?, ?, ?)
               ON CONFLICT(username, pref_key) DO UPDATE SET pref_value=excluded.pref_value""",
            (username, key, value),
        )
