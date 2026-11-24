"""Every storage backend must behave the same. Runs against SQLite always, and
against Postgres too when TEST_DATABASE_URL is set (use a throwaway database!).

    python tests/test_db_contract.py
    TEST_DATABASE_URL=postgresql://... python tests/test_db_contract.py
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402


def contract(db, label):
    u = "t_" + uuid.uuid4().hex[:8]
    # accounts
    assert db.create_user(u, "secret1")[0] is True
    ok, msg = db.create_user(u, "other")
    assert ok is False and "taken" in msg
    assert db.verify_user(u, "secret1") and not db.verify_user(u, "nope") and not db.verify_user("ghost", "x")
    # profile upsert
    assert db.get_profile(u) is None
    db.save_profile(u, 30, 150.5, 5.5, "Beginner", "")
    db.save_profile(u, 31, 151.0, 5.5, "Advanced", "bad knee")
    p = db.get_profile(u)
    assert p["age"] == 31 and p["fitness_level"] == "Advanced" and p["health_condition"] == "bad knee"
    # saved workouts: idempotent, removable
    db.save_workout(u, "Squat"); db.save_workout(u, "Squat"); db.save_workout(u, "Row")
    assert db.list_saved_workouts(u) == ["Row", "Squat"] and db.is_workout_saved(u, "Squat")
    db.unsave_workout(u, "Squat")
    assert db.list_saved_workouts(u) == ["Row"]
    # routines
    db.add_routine_item(u, "Push", "Bench", 3, 10, 30); db.add_routine_item(u, "Push", "Dips", 3, 10, 30)
    assert db.list_routines(u) == ["Push"]
    r = db.get_routine(u, "Push")
    assert [x["workout_name"] for x in r] == ["Bench", "Dips"] and r[0]["sets"] == 3 and r[0]["minutes"] == 30
    db.delete_routine(u, "Push")
    assert db.list_routines(u) == []
    # baseline lifts (PR optional)
    db.upsert_lift(u, "Bench", "upper", 185.0, 5)
    db.upsert_lift(u, "Curl", "upper", None, None)
    db.upsert_lift(u, "Bench", "upper", 195.0, 3, 6, 10, 4)  # update
    lifts = {x["exercise"]: x for x in db.list_lifts(u)}
    assert lifts["Bench"]["pr_weight"] == 195.0 and lifts["Bench"]["sets"] == 4 and lifts["Bench"]["rep_low"] == 6
    assert lifts["Curl"]["pr_weight"] is None and lifts["Curl"]["pr_reps"] is None
    db.delete_lift(u, "Curl")
    assert [x["exercise"] for x in db.list_lifts(u)] == ["Bench"]
    # logged sets
    db.log_sets(u, "s1", "2026-11-20T10:00:00", "upper", [
        {"exercise": "Bench", "set_no": 1, "weight": 135.0, "reps": 10, "is_pr": False},
        {"exercise": "Bench", "set_no": 2, "weight": 140.0, "reps": 8, "is_pr": True}])
    db.log_sets(u, "s2", "2026-11-22T10:00:00", "lower", [
        {"exercise": "Squat", "set_no": 1, "weight": 225.0, "reps": 5, "is_pr": False}])
    sets = db.list_sets(u)
    assert [s["performed_at"][:10] for s in sets] == ["2026-11-20", "2026-11-20", "2026-11-22"]
    assert sets[1]["is_pr"] is True and sets[0]["is_pr"] is False and sets[0]["weight"] == 135.0
    assert len(db.list_sets(u, "Squat")) == 1 and db.list_sets(u, "Nothing") == []
    # prefs
    assert db.get_pref(u, "unit", "lb") == "lb"
    db.set_pref(u, "unit", "kg"); db.set_pref(u, "unit", "kg")
    assert db.get_pref(u, "unit", "lb") == "kg"
    print(f"ok  {label}")


if __name__ == "__main__":
    config.DB_PATH = Path(tempfile.mkdtemp()) / "t.db"
    import db_sqlite
    contract(db_sqlite, "sqlite")
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        config.DATABASE_URL = url
        import db_postgres
        contract(db_postgres, "postgres")
    else:
        print("skip postgres (set TEST_DATABASE_URL to include it)")
    print("all passed")
