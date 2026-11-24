"""Run with:  python tests/test_research.py   (or pytest)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import research  # noqa: E402

STATUSES = {"verified", "secondary", "unverified"}


def test_entries_are_complete():
    for e in research.entries().values():
        assert e["claim"] and e["evidence"] and e["used_in"], e["id"]
        assert e["status"] in STATUSES, e["id"]


def test_sources_match_status():
    for e in research.entries().values():
        if e["status"] == "unverified":
            assert not e["source"], f"{e['id']} has a source but is marked unverified"
        else:
            assert e["source"].startswith("https://"), f"{e['id']} needs a source link"


def test_why_hides_unverified():
    assert research.why("rest-strength").endswith("))")
    assert research.why("rest-day-movement") == ""
    assert research.why("nope") == ""


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("all passed")
