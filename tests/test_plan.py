"""Run with:  python tests/test_plan.py"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import plan  # noqa: E402


def test_spread_matches_goal_and_leaves_a_day_between():
    for goal, days in plan.SPREAD.items():
        assert len(days) == goal and days == sorted(set(days)) and all(0 <= d <= 6 for d in days)
        if goal <= 3:  # beginners: a rest day between whole-body sessions
            assert all(b - a >= 2 for a, b in zip(days, days[1:])), days


def test_next_planned_wraps_into_next_week():
    p = {"0": "cur:a", "4": "cur:b"}
    assert plan.next_planned(p, after=0) == (4, "cur:b")
    assert plan.next_planned(p, after=4) == (0, "cur:a")
    assert plan.next_planned(p, after=5) == (0, "cur:a")
    assert plan.next_planned({}, after=1) is None


def test_next_planned_defaults_to_today():
    d = date.today().weekday()
    assert plan.next_planned({str(d): "cur:a"}) == (d, "cur:a")  # only today planned: next is a week away


def test_spaced_keeps_strength_days_apart():
    assert plan._spaced([0, 2, 4], 3) == [0, 2, 4]
    assert plan._spaced([0, 1, 2, 3, 4], 3) == [0, 2, 4]  # never back to back when avoidable
    assert plan._spaced([0, 1, 2, 3], 2) == [0, 3]
    assert plan._spaced([5], 1) == [5]


def test_every_goal_cites_verified_research():
    import research
    for gid, (_, _, rids) in plan.GOALS.items():
        assert rids, gid
        for rid in rids:
            e = research.get(rid)
            assert e and e["status"] != "unverified" and e["source"], (gid, rid)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("all passed")
