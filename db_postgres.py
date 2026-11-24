"""Hosted Postgres backend (Neon, Supabase, or any Postgres). Same interface as
db_sqlite.py. Enabled automatically when DATABASE_URL is set.

Why: on free hosts such as Streamlit Community Cloud the local disk is wiped when
the app restarts, so a local SQLite file loses everyone's data. A hosted
database keeps it. Neon's free plan needs no card and scales to zero when idle.

Tables are created automatically (CREATE TABLE IF NOT EXISTS).
"""
import hashlib
import hmac
import os
from functools import lru_cache

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

import config

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, salt TEXT NOT NULL, password_hash TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS profiles (
        username TEXT PRIMARY KEY, age INTEGER, weight DOUBLE PRECISION, height DOUBLE PRECISION,
        fitness_level TEXT, health_condition TEXT)""",
    """CREATE TABLE IF NOT EXISTS saved_workouts (
        username TEXT NOT NULL, workout_name TEXT NOT NULL, PRIMARY KEY (username, workout_name))""",
    """CREATE TABLE IF NOT EXISTS routines (
        id BIGSERIAL PRIMARY KEY, username TEXT NOT NULL, routine_name TEXT NOT NULL,
        workout_name TEXT NOT NULL, sets INTEGER, reps INTEGER, minutes DOUBLE PRECISION)""",
    """CREATE TABLE IF NOT EXISTS lifts (
        username TEXT NOT NULL, exercise TEXT NOT NULL, day_type TEXT NOT NULL,
        pr_weight DOUBLE PRECISION, pr_reps INTEGER, rep_low INTEGER DEFAULT 8,
        rep_high INTEGER DEFAULT 12, sets INTEGER DEFAULT 3, PRIMARY KEY (username, exercise))""",
    """CREATE TABLE IF NOT EXISTS workout_sets (
        id BIGSERIAL PRIMARY KEY, username TEXT NOT NULL, session_id TEXT NOT NULL,
        performed_at TEXT NOT NULL, day_type TEXT, exercise TEXT NOT NULL, set_no INTEGER,
        weight DOUBLE PRECISION, reps INTEGER, is_pr BOOLEAN DEFAULT FALSE)""",
    "CREATE INDEX IF NOT EXISTS idx_sets_user ON workout_sets (username, performed_at)",
    """CREATE TABLE IF NOT EXISTS user_prefs (
        username TEXT NOT NULL, pref_key TEXT NOT NULL, pref_value TEXT, PRIMARY KEY (username, pref_key))""",
]


@lru_cache(maxsize=1)
def _pool():
    # The pool re-checks a connection before handing it out, so connections that a
    # scale-to-zero host (Neon) closed while idle are replaced transparently.
    pool = ConnectionPool(
        config.DATABASE_URL, min_size=1, max_size=4, timeout=30, open=True,
        check=ConnectionPool.check_connection,
        kwargs={"row_factory": dict_row, "autocommit": True, "prepare_threshold": None},  # pgbouncer-safe
    )
    with pool.connection() as conn:
        for stmt in SCHEMA:
            conn.execute(stmt)
    return pool


def _all(sql, params=()):
    with _pool().connection() as conn:
        return conn.execute(sql, params).fetchall()


def _one(sql, params=()):
    with _pool().connection() as conn:
        return conn.execute(sql, params).fetchone()


def _run(sql, params=()):
    with _pool().connection() as conn:
        conn.execute(sql, params)


# --- accounts ---------------------------------------------------------------
def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


def create_user(username: str, password: str):
    username = username.strip()
    if not username or not password:
        return False, "Username and password are required."
    salt = os.urandom(16)
    row = _one(
        "INSERT INTO users (username, salt, password_hash) VALUES (%s, %s, %s) "
        "ON CONFLICT (username) DO NOTHING RETURNING username",
        (username, salt.hex(), _hash(password, salt)),
    )
    if not row:
        return False, "That username is already taken."
    return True, "Account created."


def verify_user(username: str, password: str) -> bool:
    row = _one("SELECT salt, password_hash FROM users WHERE username = %s", (username.strip(),))
    if not row:
        return False
    return hmac.compare_digest(_hash(password, bytes.fromhex(row["salt"])), row["password_hash"])


# --- profile ----------------------------------------------------------------
def get_profile(username: str):
    return _one("SELECT * FROM profiles WHERE username = %s", (username,))


def save_profile(username, age, weight, height, fitness_level, health_condition):
    _run(
        """INSERT INTO profiles (username, age, weight, height, fitness_level, health_condition)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (username) DO UPDATE SET
             age=EXCLUDED.age, weight=EXCLUDED.weight, height=EXCLUDED.height,
             fitness_level=EXCLUDED.fitness_level, health_condition=EXCLUDED.health_condition""",
        (username, age, weight, height, fitness_level, health_condition),
    )


# --- saved workouts ---------------------------------------------------------
def list_saved_workouts(username):
    rows = _all("SELECT workout_name FROM saved_workouts WHERE username = %s ORDER BY workout_name", (username,))
    return [r["workout_name"] for r in rows]


def is_workout_saved(username, workout_name) -> bool:
    return workout_name in set(list_saved_workouts(username))


def save_workout(username, workout_name):
    _run(
        "INSERT INTO saved_workouts (username, workout_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (username, workout_name),
    )


def unsave_workout(username, workout_name):
    _run("DELETE FROM saved_workouts WHERE username = %s AND workout_name = %s", (username, workout_name))


# --- routines ---------------------------------------------------------------
def add_routine_item(username, routine_name, workout_name, sets, reps, minutes):
    _run(
        "INSERT INTO routines (username, routine_name, workout_name, sets, reps, minutes) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (username, routine_name, workout_name, sets, reps, minutes),
    )


def list_routines(username):
    rows = _all("SELECT DISTINCT routine_name FROM routines WHERE username = %s ORDER BY routine_name", (username,))
    return [r["routine_name"] for r in rows]


def get_routine(username, routine_name):
    return _all(
        "SELECT workout_name, sets, reps, minutes FROM routines "
        "WHERE username = %s AND routine_name = %s ORDER BY id",
        (username, routine_name),
    )


def delete_routine(username, routine_name):
    _run("DELETE FROM routines WHERE username = %s AND routine_name = %s", (username, routine_name))


# --- baseline lifts ---------------------------------------------------------
def upsert_lift(username, exercise, day_type, pr_weight, pr_reps, rep_low=8, rep_high=12, sets=3):
    _run(
        """INSERT INTO lifts (username, exercise, day_type, pr_weight, pr_reps, rep_low, rep_high, sets)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (username, exercise) DO UPDATE SET
             day_type=EXCLUDED.day_type, pr_weight=EXCLUDED.pr_weight, pr_reps=EXCLUDED.pr_reps,
             rep_low=EXCLUDED.rep_low, rep_high=EXCLUDED.rep_high, sets=EXCLUDED.sets""",
        (username, exercise, day_type, pr_weight, pr_reps, rep_low, rep_high, sets),
    )


def list_lifts(username):
    return _all(
        "SELECT exercise, day_type, pr_weight, pr_reps, rep_low, rep_high, sets "
        "FROM lifts WHERE username = %s ORDER BY exercise",
        (username,),
    )


def delete_lift(username, exercise):
    _run("DELETE FROM lifts WHERE username = %s AND exercise = %s", (username, exercise))


# --- logged sets ------------------------------------------------------------
def log_sets(username, session_id, performed_at, day_type, rows):
    with _pool().connection() as conn:
        with conn.transaction():  # all sets of a workout are saved together or not at all
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO workout_sets
                       (username, session_id, performed_at, day_type, exercise, set_no, weight, reps, is_pr)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    [
                        (username, session_id, performed_at, day_type, r["exercise"], r["set_no"],
                         r["weight"], r["reps"], bool(r.get("is_pr")))
                        for r in rows
                    ],
                )


def list_sets(username, exercise=None):
    sql = ("SELECT session_id, performed_at, day_type, exercise, set_no, weight, reps, is_pr "
           "FROM workout_sets WHERE username = %s")
    params = [username]
    if exercise:
        sql += " AND exercise = %s"
        params.append(exercise)
    return _all(sql + " ORDER BY performed_at, id", params)


# --- preferences ------------------------------------------------------------
def get_pref(username, key, default=None):
    row = _one("SELECT pref_value FROM user_prefs WHERE username = %s AND pref_key = %s", (username, key))
    return row["pref_value"] if row else default


def set_pref(username, key, value):
    _run(
        """INSERT INTO user_prefs (username, pref_key, pref_value) VALUES (%s, %s, %s)
           ON CONFLICT (username, pref_key) DO UPDATE SET pref_value=EXCLUDED.pref_value""",
        (username, key, str(value)),
    )
