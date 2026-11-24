"""Run with:  python tests/test_training.py   (or pytest)"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import training as t  # noqa: E402

TODAY = date(2026, 11, 22)


def sess(days_ago, exercise, reps, weight, sid=None, day="upper"):
    when = (TODAY - timedelta(days=days_ago)).isoformat() + "T18:00:00"
    sid = sid or f"s{days_ago}"
    return [{"session_id": sid, "performed_at": when, "day_type": day, "exercise": exercise,
             "set_no": i + 1, "weight": weight, "reps": r, "is_pr": False} for i, r in enumerate(reps)]


BENCH = {"exercise": "Bench", "day_type": "upper", "pr_weight": 185, "pr_reps": 5, "rep_low": 8, "rep_high": 12, "sets": 3}
SQUAT = {**BENCH, "exercise": "Squat", "day_type": "lower"}


def test_first_session_uses_baseline_pr():
    s = t.suggest(BENCH, [], days_off=0)
    # est. max = 185*(1+5/30)=215.8 ; *0.75 = 161.9 -> nearest 5 = 160
    assert s["weight"] == 160 and s["tag"] == "start", s


def test_no_baseline_asks_user():
    s = t.suggest({**BENCH, "pr_weight": None, "pr_reps": None}, [], 0)
    assert s["weight"] is None and "First time" in s["reason"]


def test_top_of_range_once_says_one_more():
    h = t.lift_history(sess(3, "Bench", [12, 12, 12], 135), "Bench")
    s = t.suggest(BENCH, h, 3)
    assert s["weight"] == 135 and s["tag"] == "reps" and "once more" in s["reason"], s


def test_top_of_range_twice_adds_weight():  # ACSM 2009: two sessions in a row above target
    h = t.lift_history(sess(3, "Bench", [12, 12, 12], 135) + sess(6, "Bench", [12, 12, 12], 135), "Bench")
    s = t.suggest(BENCH, h, 3)
    assert s["weight"] == 140 and s["tag"] == "add" and s["reps"] == 8, s


def test_light_weight_gets_a_smaller_jump():  # 5 lb on a 20 lb dumbbell would be +25%
    h = t.lift_history(sess(3, "Bench", [12, 12, 12], 20) + sess(6, "Bench", [12, 12, 12], 20), "Bench")
    assert t.suggest(BENCH, h, 3)["weight"] == 22.5


def test_bodyweight_never_adds_pounds():
    h = t.lift_history(sess(3, "Pushups", [12, 12, 12], 0), "Pushups")
    s = t.suggest({**BENCH, "exercise": "Pushups", "pr_weight": None}, h, 3)
    assert s["weight"] == 0 and "lb" not in s["reason"] and "harder version" in s["reason"], s
    squat = sess(3, "Squat", [12, 12, 12], 225, "a", day="lower") + sess(6, "Squat", [12, 12, 12], 225, "b", day="lower")
    s = t.suggest(SQUAT, t.lift_history(squat, "Squat"), 3)
    assert s["weight"] == 235, s  # lower body jumps 10 lb


def test_hit_target_adds_a_rep():
    h = t.lift_history(sess(3, "Bench", [10, 9, 9], 135), "Bench")
    s = t.suggest(BENCH, h, 3)
    assert s["weight"] == 135 and s["reps"] == 10 and s["tag"] == "reps", s


def test_missed_once_repeats_twice_deloads():
    h = t.lift_history(sess(3, "Bench", [8, 6, 5], 135), "Bench")
    assert t.suggest(BENCH, h, 3)["tag"] == "repeat"
    h2 = t.lift_history(sess(3, "Bench", [8, 6, 5], 135) + sess(10, "Bench", [7, 6, 5], 135), "Bench")
    s = t.suggest(BENCH, h2, 3)
    assert s["tag"] == "deload" and s["weight"] == 120, s  # 135*0.9=121.5 -> 120


def test_break_eases_back_in():
    h = t.lift_history(sess(60, "Bench", [10, 10, 10], 200), "Bench")  # ~8.5 weeks off
    s = t.suggest(BENCH, h, 60)
    assert s["tag"] == "ease" and s["weight"] == 120 and s["sets"] == 2, s  # 200*0.6
    assert t.break_factor(10) == 1.0 and t.break_factor(20) == 0.9 and t.break_factor(40) == 0.75
    assert t.break_factor(90) == 0.6 and t.break_factor(300) == 0.5


def test_kg_rounding_and_steps():
    h = t.lift_history(sess(3, "Bench", [12, 12, 12], 135) + sess(6, "Bench", [12, 12, 12], 135), "Bench")  # 135 lb = 61.2 kg
    s = t.suggest(BENCH, h, 3, unit="kg")
    assert abs(t.to_unit(s["weight"], "kg") - (135 / t.LB_PER_KG + 2.5)) < 0.01, s


def test_prs():
    prior = sess(10, "Bench", [8, 8, 8], 135)
    flags, best = t.find_prs(prior, [{"weight": 135, "reps": 9}, {"weight": 140, "reps": 5}, {"weight": 140, "reps": 5}], 185, 5)
    # baseline PR is 185, so 140 is not a weight PR; 135x9 beats 135x8 -> rep PR
    assert flags == ["reps", None, None], flags
    flags, best = t.find_prs(prior, [{"weight": 190, "reps": 3}], 185, 5)
    assert flags == ["weight"] and best["weight"] == 190
    # no history, no baseline: first ever set is not a PR
    flags, _ = t.find_prs([], [{"weight": 100, "reps": 10}, {"weight": 105, "reps": 8}])
    assert flags == [None, "weight"], flags  # the first set sets the bar; beating it later counts


def test_split_and_lineup():
    lifts = [
        {"exercise": "Bench", "day_type": "upper"}, {"exercise": "Row", "day_type": "upper"},
        {"exercise": "OHP", "day_type": "upper"}, {"exercise": "Curl", "day_type": "upper"}, {"exercise": "Dips", "day_type": "upper"},
        {"exercise": "Squat", "day_type": "lower"}, {"exercise": "RDL", "day_type": "lower"},
        {"exercise": "Plank", "day_type": "core"},
    ]
    assert t.suggest_split("upper") == "lower" and t.suggest_split("lower") == "upper"
    assert t.suggest_split(None) == "full" and t.suggest_split(None, has_lower=False) == "upper"
    done = sess(2, "Bench", [10], 135) + sess(2, "Row", [10], 135)
    up = t.pick_lineup(lifts, "upper", done, 4)
    # the 3 untrained lifts come first, then the one trained longest ago (Bench/Row tie -> alphabetical)
    assert set(up) == {"OHP", "Curl", "Dips", "Bench"} and "Row" not in up, up
    full = t.pick_lineup(lifts, "full", [], 4)
    assert len(full) == 4 and {"Squat", "RDL"} <= set(full), full
    lower = t.pick_lineup(lifts, "lower", [], 4)
    assert lower == ["RDL", "Squat", "Plank"], lower  # fewer than 4 lower lifts: core fills in


def test_lineup_prefers_lifts_with_a_pr():
    lifts = [{"exercise": "A-no-pr", "day_type": "lower", "pr_weight": None},
             {"exercise": "B-pr", "day_type": "lower", "pr_weight": 100},
             {"exercise": "C-pr", "day_type": "lower", "pr_weight": 120}]
    assert t.pick_lineup(lifts, "lower", [], 2) == ["B-pr", "C-pr"]


def test_feel_adjusts_the_plan():
    top = t.lift_history(sess(3, "Bench", [12, 12, 12], 135), "Bench")
    assert t.suggest(BENCH, top, 3)["tag"] == "reps"                      # no feedback: one more session first
    assert t.suggest(BENCH, top, 3, feel="easy")["tag"] == "add"          # felt easy: add now
    assert t.suggest(BENCH, top, 3, feel="hard")["tag"] == "repeat"       # hit the range but it was hard: hold
    mid = t.lift_history(sess(3, "Bench", [10, 9, 9], 135), "Bench")
    assert t.suggest(BENCH, mid, 3)["tag"] == "reps"
    s = t.suggest(BENCH, mid, 3, feel="easy")
    assert s["tag"] == "add" and s["weight"] == 140                        # easy: don't wait for the top of the range
    s = t.suggest(BENCH, mid, 3, feel="pain")
    assert s["tag"] == "ease" and s["weight"] == 110 and "hurt" in s["reason"]  # 135*0.8=108 -> 110


def test_milestones():
    assert t.milestone_crossed(220, 230) == "First time over 225 lb"
    assert t.milestone_crossed(300, 330) == "First time over 315 lb"
    assert t.milestone_crossed(135, 140) is None            # no round number crossed
    assert t.milestone_crossed(None, 500) is None            # no previous best: nothing to 'cross'
    assert t.milestone_crossed(90, 230) == "First time over 225 lb"   # biggest number crossed wins
    assert t.milestone_crossed(130, 140, "kg") == "First time over 60 kg"  # 130 lb ~ 59 kg -> 140 lb ~ 63.5 kg


def test_streak():
    sets = sess(0, "Bench", [5], 100) + sess(2, "Bench", [5], 100) + sess(30, "Bench", [5], 100)
    this_week, since = t.streak_summary(sets, TODAY)
    assert since == 0 and this_week == 2, (this_week, since)  # 2026-11-22 is a Sunday
    assert t.week_dots(sets, TODAY)[6] is True


def test_amount_speaks_each_unit():
    assert t.amount(0, 50, "lb", "hold") == "50 seconds"
    assert t.amount(0, 1, "lb", "hold") == "1 second"
    assert t.amount(0, 30, "kg", "minutes") == "30 minutes"
    assert t.amount(0, 12, "lb") == "12 reps"          # bodyweight: never "0 lb × 12"
    assert t.amount(135, 8, "lb") == "135 lb × 8"
    assert "kg" in t.amount(135, 8, "kg")


def test_kind_of_knows_holds_and_walks():
    assert t.kind_of("Child's Pose") == "hold" and t.kind_of("Plank") == "hold"
    assert t.kind_of("Walk: Brisk walk", "cardio") == "minutes"
    assert t.kind_of("Barbell Squat") == "reps"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("all passed")
