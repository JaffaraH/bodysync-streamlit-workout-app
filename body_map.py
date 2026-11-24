"""Which muscles a list of exercises works, said in plain words (Free Exercise DB muscle names).
A drawn body figure was tried and removed: hand-drawn shapes looked odd, and no free body-map art fit."""
from html import escape

NICE = {"abdominals": "abs", "quadriceps": "quads", "middle back": "upper back", "adductors": "inner thighs",
        "abductors": "outer hips"}


def muscles_for(exercises):
    """(main, also): muscle sets from a list of exercise dicts. A muscle that is main anywhere counts as main."""
    main = {m for e in exercises for m in (e.get("primaryMuscles") or [])}
    also = {m for e in exercises for m in (e.get("secondaryMuscles") or [])} - main
    return main, also


def nice(m):
    return NICE.get(m, m)


def works_line(main, also):
    """'**Works** chest, triceps · also shoulders' (markdown)."""
    words = lambda ms: ", ".join(sorted(nice(m) for m in ms))
    return f"**Works** {escape(words(main))}" + (f"  ·  also {escape(words(also))}" if also else "")
