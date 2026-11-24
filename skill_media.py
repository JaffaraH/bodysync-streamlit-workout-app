"""Demo media for skill steps.

Lookup order, so a step never shows the wrong exercise:
1. A hand-picked clip you drop in ``static/skills/<step id>.webp|gif|mp4|jpg``.
2. The Free Exercise DB photos named by the step's ``library`` field.
3. Nothing (the written steps are shown on their own).

``python skill_media.py`` prints which steps still have no picture.
"""
from pathlib import Path

import config

SKILLS_DIR = Path(config.LOGO_PATH).parent / "skills"
EXTS = (".webp", ".gif", ".mp4", ".jpg", ".png")


def clip(step):
    """URL of a hand-picked clip for this step, or None."""
    for ext in EXTS:
        if (SKILLS_DIR / f"{step['id']}{ext}").exists():
            return f"/app/static/skills/{step['id']}{ext}"
    return None


def has_media(step, find_exercise):
    return bool(clip(step) or (step.get("library") and find_exercise(step["library"])))


if __name__ == "__main__":
    import skills_logic
    from exercise_data import find_exercise

    for lad in skills_logic.ladders().values():
        for s in lad["steps"]:
            if not has_media(s, find_exercise):
                print(f"{lad['id']:18} {s['id']:14} {s['name']}")
