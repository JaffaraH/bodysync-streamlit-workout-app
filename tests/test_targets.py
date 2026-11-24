"""Run with:  python tests/test_targets.py   (or pytest)"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import research  # noqa: E402
import targets  # noqa: E402

TODAY = date(2026, 11, 24)
WORKOUTS = json.loads((ROOT / "curated_workouts.json").read_text())["workouts"]


def logged(days_ago, exercise, reps, weight, pr=False, day="upper"):
    when = (TODAY - timedelta(days=days_ago)).isoformat() + "T18:00:00"
    return [{"session_id": f"s{days_ago}", "performed_at": when, "day_type": day, "exercise": exercise,
             "set_no": i + 1, "weight": weight, "reps": r, "is_pr": pr and i == 0} for i, r in enumerate(reps)]


def test_every_curated_move_says_what_it_works():
    for w in WORKOUTS:
        for e in w["exercises"]:
            m = targets.move(e[0])
            assert m and m["area"] and m["job"], f"{w['id']}: {e[0]} has no target"
            assert targets.works(e[0]).startswith("Works: ")


def test_every_curated_workout_has_a_goal_note():
    for w in WORKOUTS:
        note = targets.goal_note(w)
        assert note and note["title"] and note["lines"], w["id"]
        assert note["expect"]["lines"]


def test_everything_cited_is_verified():
    for rid in targets.all_research_ids():
        e = research.get(rid)
        assert e and e["status"] == "verified" and e["source"].startswith("https://"), rid


def test_plain_language_rules():
    d = targets.data()
    text = [m["job"] for m in d["moves"].values()] + [x for g in d["goals"].values() for x in g["lines"]]
    for t in text:
        assert t.isascii(), f"no emoji or special characters: {t}"
        assert t.endswith((".", "?")), t


def test_unknown_move_shows_nothing():
    assert targets.move("My own move") is None and targets.works("My own move") == ""
    assert targets.move("Skill: Plank") == targets.move("Plank")


def test_stuck_needs_four_weeks():
    sets = logged(20, "Bench", [8, 8], 100) + logged(5, "Bench", [8, 8], 100)
    assert targets.stuck(sets, TODAY) is None


def test_stuck_after_four_weeks_without_a_record():
    sets = logged(40, "Bench", [8], 100, pr=True) + logged(20, "Bench", [8, 8], 100) + logged(10, "Bench", [8, 8], 100) \
        + logged(3, "Bench", [8, 8], 100)
    s = targets.stuck(sets, TODAY)
    assert s and s["days"] == 3 and s["lift"] == "Bench" and not s["moved"], s
    assert abs(s["per_week"] - 0.75) < 1e-9


def test_reps_up_counts_as_moving():
    sets = logged(40, "Bench", [8], 100) + logged(20, "Bench", [8], 100) + logged(3, "Bench", [10], 100)
    assert targets.stuck(sets, TODAY)["moved"]


def test_a_recent_record_means_not_stuck():
    sets = logged(40, "Bench", [8], 100) + logged(10, "Bench", [9], 100, pr=True)
    assert targets.stuck(sets, TODAY) is None


def test_no_recent_lifting_means_not_stuck():
    sets = logged(60, "Bench", [8], 100) + logged(5, "Walk: brisk", [30], 0, day="cardio")
    assert targets.stuck(sets, TODAY) is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("all passed")
