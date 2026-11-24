"""FitBuddy's AI answers are checked before anything is saved; no AI call is made here."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ai  # noqa: E402
import chat  # noqa: E402

day = {"exercises": [
    {"name": "Pushups", "sets": 3, "reps": 12},
    {"name": "Made Up Exercise", "sets": 3, "reps": 10},       # not in the library: left out
    {"name": "Plank", "sets": 99, "reps": 45, "seconds": True},  # sets clamped to 8, kept as seconds
    {"name": "Bodyweight Squat", "sets": "x", "reps": None},     # bad numbers: sensible defaults
]}
moves, skipped = chat.clean_day(day)
assert skipped == 1
assert moves[0] == ("Pushups", 3, 12, False)
assert moves[1] == ("Plank", 8, 45, True)
assert moves[2] == ("Bodyweight Squat", 3, 10, False)

# equipment filter: bodyweight only never offers a barbell move
names = chat._library_for(["body only"])
assert "Pushups" in names and "Barbell Squat" not in names

# a retired model is recognised (so the next one is tried); other errors are not
assert ai._retired(Exception("404 NOT_FOUND models/gemini-x is not found"))
assert not ai._retired(Exception("429 RESOURCE_EXHAUSTED"))
assert ai._models()[0] == ai.config.GEMINI_MODEL and "gemini-2.5-flash-lite" in ai._models()
# AI text is shown without images (they'd load from any address) or hidden links; formatting stays
import ui  # noqa: E402
assert ui.no_media("Eat ![x](http://evil/p.png) eggs [click](http://evil) now **bold**") == "Eat  eggs click now **bold**"
print("all passed")
