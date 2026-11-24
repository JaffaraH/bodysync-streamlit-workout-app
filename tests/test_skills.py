"""Run with:  python tests/test_skills.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skills_logic as sk  # noqa: E402


def test_ladders_are_well_formed():
    L = sk.ladders()
    assert len(L) >= 5 and "first-pushup" in L
    for lid, lad in L.items():
        assert lad["title"] and lad["steps"] and lad["warmup"], lid
        ids = [s["id"] for s in lad["steps"]]
        assert len(ids) == len(set(ids)), f"duplicate step ids in {lid}"
        for s in lad["steps"]:
            assert s["kind"] in ("reps", "hold") and s["sets"] >= 1 and s["target"] >= 1 and s["how"], (lid, s["id"])


def test_library_names_exist_if_present():
    import json
    p = Path("/private/tmp/bs_test4/exercises.json")
    if not p.exists():
        return  # exercise data not downloaded here: skip
    names = {e["name"] for e in json.loads(p.read_text())}
    for lad in sk.ladders().values():
        for s in lad["steps"]:
            assert s["library"] is None or s["library"] in names, (lad["id"], s["library"])


def test_form_cues_match_the_library():
    import json
    cues = {k: v for k, v in json.loads((Path(__file__).resolve().parent.parent / "form_cues.json").read_text()).items() if not k.startswith("_")}
    assert len(cues) >= 15
    for name, tip in cues.items():
        assert len(tip["cues"]) == 3 and tip["watch"] and tip["feel"] and tip["easier"], name
    p = Path("/private/tmp/bs_test4/exercises.json")
    if p.exists():
        names = {e["name"] for e in json.loads(p.read_text())}
        missing = [n for n in cues if n not in names]
        assert not missing, missing


def test_evaluate():
    step = {"sets": 3, "target": 10, "kind": "reps"}
    assert sk.evaluate(step, [10, 11, 10])["hit"] is True
    assert sk.evaluate(step, [10, 9, 10])["hit"] is False
    assert sk.evaluate(step, [12, 12])["hit"] is False   # fewer sets than required
    assert sk.evaluate(step, [12, 12, 12, 3])["hit"] is True  # extra sets don't count against you


def test_level_up_needs_two_clears_in_a_row():
    s = sk.new_state()
    s, e = sk.advance(s, True, 6);  assert e == "clear" and s["step"] == 0 and s["streak"] == 1
    s, e = sk.advance(s, False, 6); assert e == "miss" and s["streak"] == 0   # a miss resets the streak
    s, e = sk.advance(s, True, 6);  assert e == "clear"
    s, e = sk.advance(s, True, 6);  assert e == "level_up" and s["step"] == 1 and s["streak"] == 0


def test_complete_on_last_step():
    s = {"step": 5, "streak": 1, "done": False}
    s, e = sk.advance(s, True, 6)
    assert e == "complete" and s["done"] is True and s["step"] == 5


def test_target_text():
    assert sk.target_text({"kind": "hold", "sets": 3, "target": 20}) == "3 × 20s hold"
    assert sk.target_text({"kind": "reps", "sets": 3, "target": 5, "per_side": True}) == "3 × 5 reps per side"


def test_any_way_clears_a_step():
    L = sk.ladders()
    knee = next(x for x in L["first-pushup"]["steps"] if x["id"] == "knee")
    ways = sk.ways(knee)
    assert ways[0] is knee and len(ways) >= 2
    slow = next(w for w in ways if w["id"] == "knee-slow")
    assert sk.evaluate(slow, [6, 6, 6])["hit"]          # the alternative's own target counts
    assert not sk.evaluate(knee, [6, 6, 6])["hit"]      # (the main way would need 10)


def test_alternatives_are_well_formed():
    for lad in sk.ladders().values():
        for step in lad["steps"]:
            for o in step.get("options") or []:
                assert o["name"] and o["kind"] in ("reps", "hold") and o["sets"] >= 1 and o["target"] >= 1, (lad["id"], o)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("all passed")
