"""Drive storage against a simulated Google Drive.   python tests/test_drive.py"""
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db_drive as d  # noqa: E402


class FakeDrive:
    """Just enough of the Drive v3 API: list / download / create (multipart) / update (media)."""

    def __init__(self):
        self.files = {}      # id -> json text
        self.calls = []      # (method, kind)
        self.token_ok = True

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        params = params or {}
        assert headers["Authorization"].startswith("Bearer "), "every call must be authorised"
        if not self.token_ok:
            return SimpleNamespace(status_code=401, json=lambda: {})
        if method == "GET" and url.endswith("/files"):
            assert params["spaces"] == "appDataFolder", "must only touch the private app-data folder"
            self.calls.append(("GET", "list"))
            return SimpleNamespace(status_code=200, json=lambda: {"files": [{"id": i} for i in self.files]})
        if method == "GET" and "/files/" in url and params.get("alt") == "media":
            self.calls.append(("GET", "download"))
            return SimpleNamespace(status_code=200, json=lambda: json.loads(self.files[url.rsplit("/", 1)[1]]))
        if method == "PATCH":
            self.calls.append(("PATCH", "update"))
            self.files[url.rsplit("/", 1)[1]] = data.decode()
            return SimpleNamespace(status_code=200, json=lambda: {})
        if method == "POST":
            self.calls.append(("POST", "create"))
            text = data.decode()
            assert '"parents": ["appDataFolder"]' in text, "new file must be created in the app-data folder"
            body = re.search(r"Content-Type: application/json\r\n\r\n(.*)\r\n--\w+--", text, re.S).group(1)
            fid = f"file{len(self.files) + 1}"
            self.files[fid] = body
            return SimpleNamespace(status_code=200, json=lambda: {"id": fid})
        raise AssertionError((method, url))


def connect(drive, session=None):
    d.requests.request = drive.request
    d._token = lambda: "token"
    d._session = lambda: session if session is not None else sess
    return session


def test_save_reload_and_batching():
    global sess
    drive = FakeDrive()
    sess = {}
    connect(drive)
    u = "me@example.com"
    d.save_profile(u, None, None, None, "Beginner", "")          # age/weight/height are optional
    d.upsert_lift(u, "Bench", "upper", 185.0, 5)
    d.upsert_lift(u, "Curl", "upper", None, None)
    d.save_workout(u, "Squat"); d.save_workout(u, "Squat")
    d.add_routine_item(u, "Push", "Bench", 3, 10, 30)
    d.log_sets(u, "s1", "2026-11-20T10:00:00", "upper", [
        {"exercise": "Bench", "set_no": 1, "weight": 135.0, "reps": 10, "is_pr": False},
        {"exercise": "Bench", "set_no": 2, "weight": 140.0, "reps": 8, "is_pr": True}])
    d.set_pref(u, "unit", "kg")
    assert d.has_unsaved()
    d.flush()
    assert [c for c in drive.calls if c[0] in ("POST", "PATCH")] == [("POST", "create")], "many changes, ONE upload"
    n = len(drive.calls)
    d.flush()
    assert len(drive.calls) == n, "flushing with nothing changed must not hit the network"

    # a second device / fresh session sees everything
    sess2 = {}
    connect(drive, sess2)
    assert d.get_profile(u)["fitness_level"] == "Beginner" and d.get_profile(u)["age"] is None
    assert {l["exercise"]: l["pr_weight"] for l in d.list_lifts(u)} == {"Bench": 185.0, "Curl": None}
    assert d.list_saved_workouts(u) == ["Squat"] and d.is_workout_saved(u, "Squat")
    assert d.list_routines(u) == ["Push"] and d.get_routine(u, "Push")[0]["minutes"] == 30
    sets = d.list_sets(u)
    assert [s["weight"] for s in sets] == [135.0, 140.0] and sets[1]["is_pr"] is True and len(d.list_sets(u, "Nope")) == 0
    assert d.get_pref(u, "unit", "lb") == "kg" and d.get_pref(u, "x", "dflt") == "dflt"

    # edits update the same file (PATCH, not a second file)
    d.delete_lift(u, "Curl"); d.unsave_workout(u, "Squat"); d.delete_routine(u, "Push")
    d.flush()
    assert len(drive.files) == 1 and drive.calls[-1] == ("PATCH", "update")
    saved = json.loads(next(iter(drive.files.values())))
    assert "Curl" not in saved["lifts"] and saved["saved"] == [] and saved["routines"] == []


def test_expired_google_connection():
    global sess
    drive = FakeDrive()
    drive.token_ok = False
    sess = {}
    connect(drive)
    try:
        d.list_lifts("x")
        assert False, "should have raised"
    except d.DriveAuthError:
        pass


def test_unsaved_data_survives_a_failed_upload():
    global sess
    drive = FakeDrive()
    sess = {}
    connect(drive)
    d.upsert_lift("x", "Bench", "upper", 100.0, 5)
    drive.token_ok = False
    try:
        d.flush()
        assert False
    except d.DriveAuthError:
        pass
    assert d.has_unsaved(), "still marked unsaved so the next run retries"
    drive.token_ok = True
    d.flush()
    assert not d.has_unsaved() and len(drive.files) == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("all passed")
