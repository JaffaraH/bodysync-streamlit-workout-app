"""Exercises people create: same shape as the database's, holds counted in seconds, photos become a demo."""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

import exercise_data  # noqa: E402
import training  # noqa: E402


def _photo(color):
    buf = io.BytesIO()
    Image.new("RGB", (600, 400), color).save(buf, "PNG")
    buf.seek(0)
    return buf


ex = exercise_data.make_custom("Total Gym Row", "lats", "machine", False, "Sit facing in.\nPull.\n\nLower.",
                               [_photo("red"), _photo("blue")])
assert ex["custom"] and ex["id"] == "custom-total-gym-row" and ex["primaryMuscles"] == ["lats"]
assert ex["instructions"] == ["Sit facing in.", "Pull.", "Lower."]  # blank lines dropped
assert len(ex["photos"]) == 2 and all(isinstance(p, str) for p in ex["photos"])  # stored as text (base64)

hold = exercise_data.make_custom("Wall Sit", "quadriceps", None, True, "", [])
assert hold["hold"] and hold["equipment"] == "body only" and hold["photos"] == []

# the hold hook: training can't see the session, exercise_data plugs a function in
training.EXTRA_HOLDS = lambda: {"Wall Sit"}
assert training.kind_of("Wall Sit") == "hold" and training.kind_of("Total Gym Row") == "reps"
print("all passed")
