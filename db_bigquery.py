"""Optional BigQuery backend: the project's original cloud database.

Enable with  BODYSYNC_DB=bigquery  (plus GCP_PROJECT_ID and Google credentials).
It uses the SAME dataset and tables as the original app, so existing accounts,
profiles and saved workouts keep working:

    <project>.bodysyncusers.user_info      (username, password)
    <project>.bodysyncusers.saved_profile  (username, age, weight, height, fitness_level, health_condition)
    <project>.bodysyncusers.saved_workouts (username, workout_name)
    <project>.bodysyncusers.user_workout   (username, workout_name, workout_playlist, reps, minutes, ss)

Compatibility notes:
* Passwords stay as unsalted SHA-256 hex, exactly as the original app stored
  them, otherwise existing users could no longer log in.
* user_workout columns are mapped the way the original app WROTE them:
  sets -> `reps`, reps -> `minutes`, minutes -> `ss`.
* Missing dataset/tables are created automatically (CREATE ... IF NOT EXISTS);
  existing ones are never altered.

IMPORTANT: this app writes with INSERT / MERGE / DELETE (DML). Google's free
"sandbox" (no billing account) does not support DML, so this backend needs a
project with billing enabled (the free usage tier still applies, but a card is
required). For a free hosted copy prefer the default SQLite or a free Postgres.

This backend was written against the original table layout but has not been
exercised against a live BigQuery project.
"""
import hashlib
import hmac
from functools import lru_cache

from google.cloud import bigquery

import config

_SCHEMAS = {
    "user_info": "username STRING, password STRING",
    "saved_profile": "username STRING, age INT64, weight FLOAT64, height FLOAT64, "
                     "fitness_level STRING, health_condition STRING",
    "saved_workouts": "username STRING, workout_name STRING",
    "user_workout": "username STRING, workout_name STRING, workout_playlist STRING, "
                    "reps INT64, minutes FLOAT64, ss INT64",
    # --- added for baseline lifts / Today's workout (new tables, nothing existing is altered)
    "lifts": "username STRING, exercise STRING, day_type STRING, pr_weight FLOAT64, pr_reps INT64, "
             "rep_low INT64, rep_high INT64, sets INT64",
    "workout_sets": "username STRING, session_id STRING, performed_at STRING, day_type STRING, "
                    "exercise STRING, set_no INT64, weight FLOAT64, reps INT64, is_pr BOOL",
    "user_prefs": "username STRING, pref_key STRING, pref_value STRING",
}


@lru_cache(maxsize=1)
def _client():
    credentials = None
    try:  # hosted copy: service-account JSON pasted into Streamlit secrets as [gcp_service_account]
        import streamlit as st
        from google.oauth2 import service_account

        if "gcp_service_account" in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]))
    except Exception:
        credentials = None
    client = bigquery.Client(project=config.GCP_PROJECT_ID or None, credentials=credentials)
    try:  # best effort: needs create permissions, harmless if they already exist
        client.create_dataset(f"{client.project}.{config.BQ_DATASET}", exists_ok=True)
        for table, cols in _SCHEMAS.items():
            client.query(f"CREATE TABLE IF NOT EXISTS {_t(client, table)} ({cols})").result()
    except Exception:
        pass
    return client


def _t(client, table):
    return f"`{client.project}.{config.BQ_DATASET}.{table}`"


def _q(sql_template, params=(), fetch=True):
    """Run a query. `sql_template` may contain {t_<table>} placeholders."""
    client = _client()
    sql = sql_template.format(**{f"t_{t}": _t(client, t) for t in _SCHEMAS})
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter(n, ty, v) for n, ty, v in params]
        ),
    )
    result = job.result()
    return list(result) if fetch else None


def _sha(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# --- accounts ---------------------------------------------------------------
def create_user(username: str, password: str):
    username = username.strip()
    if not username or not password:
        return False, "Username and password are required."
    if _q("SELECT 1 FROM {t_user_info} WHERE username = @u LIMIT 1", [("u", "STRING", username)]):
        return False, "That username is already taken."
    _q(
        "INSERT INTO {t_user_info} (username, password) VALUES (@u, @p)",
        [("u", "STRING", username), ("p", "STRING", _sha(password))],
        fetch=False,
    )
    return True, "Account created."


def verify_user(username: str, password: str) -> bool:
    rows = _q(
        "SELECT password FROM {t_user_info} WHERE username = @u LIMIT 1",
        [("u", "STRING", username.strip())],
    )
    return bool(rows) and hmac.compare_digest(_sha(password), rows[0]["password"])


# --- profile ----------------------------------------------------------------
def get_profile(username: str):
    rows = _q(
        "SELECT age, weight, height, fitness_level, health_condition "
        "FROM {t_saved_profile} WHERE username = @u LIMIT 1",
        [("u", "STRING", username)],
    )
    return {"username": username, **dict(rows[0])} if rows else None


def save_profile(username, age, weight, height, fitness_level, health_condition):
    # MERGE = update if the user already has a row, else insert (the original
    # app inserted a duplicate row on every save).
    _q(
        """MERGE {t_saved_profile} T
           USING (SELECT @u AS username, @age AS age, @w AS weight, @h AS height,
                         @lvl AS fitness_level, @hc AS health_condition) S
           ON T.username = S.username
           WHEN MATCHED THEN UPDATE SET age = S.age, weight = S.weight, height = S.height,
                fitness_level = S.fitness_level, health_condition = S.health_condition
           WHEN NOT MATCHED THEN INSERT (username, age, weight, height, fitness_level, health_condition)
                VALUES (S.username, S.age, S.weight, S.height, S.fitness_level, S.health_condition)""",
        [
            ("u", "STRING", username), ("age", "INT64", None if age is None else int(age)),
            ("w", "FLOAT64", None if weight is None else float(weight)),
            ("h", "FLOAT64", None if height is None else float(height)), ("lvl", "STRING", fitness_level),
            ("hc", "STRING", health_condition or ""),
        ],
        fetch=False,
    )


# --- saved workouts ---------------------------------------------------------
def list_saved_workouts(username):
    rows = _q(
        "SELECT DISTINCT workout_name FROM {t_saved_workouts} WHERE username = @u ORDER BY workout_name",
        [("u", "STRING", username)],
    )
    return [r["workout_name"] for r in rows]


def is_workout_saved(username, workout_name) -> bool:
    return workout_name in set(list_saved_workouts(username))


def save_workout(username, workout_name):
    _q(
        """MERGE {t_saved_workouts} T
           USING (SELECT @u AS username, @w AS workout_name) S
           ON T.username = S.username AND T.workout_name = S.workout_name
           WHEN NOT MATCHED THEN INSERT (username, workout_name) VALUES (S.username, S.workout_name)""",
        [("u", "STRING", username), ("w", "STRING", workout_name)],
        fetch=False,
    )


def unsave_workout(username, workout_name):
    _q(
        "DELETE FROM {t_saved_workouts} WHERE username = @u AND workout_name = @w",
        [("u", "STRING", username), ("w", "STRING", workout_name)],
        fetch=False,
    )


# --- routines (table user_workout; see column mapping note above) -----------
def add_routine_item(username, routine_name, workout_name, sets, reps, minutes):
    _q(
        "INSERT INTO {t_user_workout} (username, workout_name, workout_playlist, reps, minutes, ss) "
        "VALUES (@u, @w, @r, @sets, @reps, @mins)",
        [
            ("u", "STRING", username), ("w", "STRING", workout_name), ("r", "STRING", routine_name),
            ("sets", "INT64", int(sets)), ("reps", "FLOAT64", float(reps)), ("mins", "INT64", int(minutes)),
        ],
        fetch=False,
    )


def list_routines(username):
    rows = _q(
        "SELECT DISTINCT workout_playlist FROM {t_user_workout} WHERE username = @u ORDER BY workout_playlist",
        [("u", "STRING", username)],
    )
    return [r["workout_playlist"] for r in rows]


def get_routine(username, routine_name):
    rows = _q(
        "SELECT workout_name, reps, minutes, ss FROM {t_user_workout} "
        "WHERE username = @u AND workout_playlist = @r",
        [("u", "STRING", username), ("r", "STRING", routine_name)],
    )
    return [
        {"workout_name": r["workout_name"], "sets": r["reps"],
         "reps": int(r["minutes"] or 0), "minutes": r["ss"]}
        for r in rows
    ]


def delete_routine(username, routine_name):
    _q(
        "DELETE FROM {t_user_workout} WHERE username = @u AND workout_playlist = @r",
        [("u", "STRING", username), ("r", "STRING", routine_name)],
        fetch=False,
    )


# --- baseline lifts -----------------------------------------------------------
def upsert_lift(username, exercise, day_type, pr_weight, pr_reps, rep_low=8, rep_high=12, sets=3):
    _q(
        """MERGE {t_lifts} T
           USING (SELECT @u AS username, @e AS exercise, @d AS day_type, @w AS pr_weight, @r AS pr_reps,
                         @lo AS rep_low, @hi AS rep_high, @s AS sets) S
           ON T.username = S.username AND T.exercise = S.exercise
           WHEN MATCHED THEN UPDATE SET day_type = S.day_type, pr_weight = S.pr_weight, pr_reps = S.pr_reps,
                rep_low = S.rep_low, rep_high = S.rep_high, sets = S.sets
           WHEN NOT MATCHED THEN INSERT (username, exercise, day_type, pr_weight, pr_reps, rep_low, rep_high, sets)
                VALUES (S.username, S.exercise, S.day_type, S.pr_weight, S.pr_reps, S.rep_low, S.rep_high, S.sets)""",
        [
            ("u", "STRING", username), ("e", "STRING", exercise), ("d", "STRING", day_type),
            ("w", "FLOAT64", None if pr_weight is None else float(pr_weight)),
            ("r", "INT64", None if pr_reps is None else int(pr_reps)),
            ("lo", "INT64", int(rep_low)), ("hi", "INT64", int(rep_high)), ("s", "INT64", int(sets)),
        ],
        fetch=False,
    )


def list_lifts(username):
    rows = _q(
        "SELECT exercise, day_type, pr_weight, pr_reps, rep_low, rep_high, sets "
        "FROM {t_lifts} WHERE username = @u ORDER BY exercise",
        [("u", "STRING", username)],
    )
    return [dict(r) for r in rows]


def delete_lift(username, exercise):
    _q(
        "DELETE FROM {t_lifts} WHERE username = @u AND exercise = @e",
        [("u", "STRING", username), ("e", "STRING", exercise)],
        fetch=False,
    )


# --- logged sets --------------------------------------------------------------
def log_sets(username, session_id, performed_at, day_type, rows):
    """One batch load job for all sets (one round trip instead of one query per set)."""
    client = _client()
    payload = [
        {
            "username": username, "session_id": session_id, "performed_at": performed_at,
            "day_type": day_type, "exercise": r["exercise"], "set_no": int(r["set_no"]),
            "weight": float(r["weight"]), "reps": int(r["reps"]), "is_pr": bool(r.get("is_pr")),
        }
        for r in rows
    ]
    schema = [
        bigquery.SchemaField(n, t) for n, t in [
            ("username", "STRING"), ("session_id", "STRING"), ("performed_at", "STRING"),
            ("day_type", "STRING"), ("exercise", "STRING"), ("set_no", "INT64"),
            ("weight", "FLOAT64"), ("reps", "INT64"), ("is_pr", "BOOL"),
        ]
    ]
    job = client.load_table_from_json(
        payload,
        f"{client.project}.{config.BQ_DATASET}.workout_sets",
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_APPEND"),
    )
    job.result()


def list_sets(username, exercise=None):
    sql = ("SELECT session_id, performed_at, day_type, exercise, set_no, weight, reps, is_pr "
           "FROM {t_workout_sets} WHERE username = @u")
    params = [("u", "STRING", username)]
    if exercise:
        sql += " AND exercise = @e"
        params.append(("e", "STRING", exercise))
    rows = _q(sql + " ORDER BY performed_at, set_no", params)
    return [{**dict(r), "is_pr": bool(r["is_pr"])} for r in rows]


# --- preferences --------------------------------------------------------------
def get_pref(username, key, default=None):
    rows = _q(
        "SELECT pref_value FROM {t_user_prefs} WHERE username = @u AND pref_key = @k LIMIT 1",
        [("u", "STRING", username), ("k", "STRING", key)],
    )
    return rows[0]["pref_value"] if rows else default


def set_pref(username, key, value):
    _q(
        """MERGE {t_user_prefs} T
           USING (SELECT @u AS username, @k AS pref_key, @v AS pref_value) S
           ON T.username = S.username AND T.pref_key = S.pref_key
           WHEN MATCHED THEN UPDATE SET pref_value = S.pref_value
           WHEN NOT MATCHED THEN INSERT (username, pref_key, pref_value) VALUES (S.username, S.pref_key, S.pref_value)""",
        [("u", "STRING", username), ("k", "STRING", key), ("v", "STRING", str(value))],
        fetch=False,
    )
