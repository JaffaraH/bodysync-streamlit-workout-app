"""Form guidance: a demo you can watch plus a few plain cues, always one tap away."""
import json
from functools import lru_cache
from pathlib import Path

import streamlit as st

from exercise_data import exercise_gif, find_exercise

CUES_PATH = Path(__file__).resolve().parent / "form_cues.json"
FEELS = ["Easy", "Just right", "Hard", "Pain"]
FEEL_HELP = (
    "Easy: you could have done 3 or more extra reps. Just right: 1 or 2 more. Hard: you couldn't do another. "
    "Pain: something hurt (not just effort). Your answer adjusts next time's weight."
)


# Free Exercise DB has exactly two photos per exercise (a start and an end; checked: 873 of 876 have 2, 3 have 0).
# A circle or a quick back-and-forth can't be shown with two, so those moves say so and show their steps.
MOTION_WORDS = {"circle": "moves in a circle", "flutter": "is a quick, small up-and-down", "scissor": "crosses back and forth",
                "windmill": "swings across your body", "kick": "is a quick, repeated kick", "roll": "rolls through"}


def motion_note(name):
    """'' for most moves; for ones two photos can't show, a plain note saying what the move really does."""
    low = name.lower()
    word = next((v for k, v in MOTION_WORDS.items() if k in low), None)
    return f"The demo has only a start and an end photo, but this move {word}. Follow the steps." if word else ""


def steps(name, limit=4):
    ex = find_exercise(name)
    return [s for s in (ex or {}).get("instructions") or []][:limit]


@lru_cache(maxsize=1)
def cues():
    data = json.loads(CUES_PATH.read_text())
    return {k: v for k, v in data.items() if not k.startswith("_")}


def render(name, key):
    """A visible 'How to do it' button that opens the demo and cues in a dialog (no hidden expander)."""
    if st.button("How to do it", icon=":material/lightbulb:", type="tertiary", key=f"tips_{key}"):
        _tips_dialog(name)


@st.dialog("How to do it", width="large")
def _tips_dialog(name):
    """Form tips for one exercise: demo, cues, what to watch for, where you should feel it."""
    ex = find_exercise(name)
    tip = cues().get(name)
    st.markdown(f"**{name}**")
    demo, text = st.columns([1, 1.6])
    with demo:
        path = exercise_gif(ex) if ex else None
        if path:  # an <img> keeps the animation (st.image re-encodes WebP to one frame)
            import ui
            ui.demo(path)
            st.caption(motion_note(name) or
                       "Start at 1, move to 2, then come back to 1. That's one rep. For a hold or stretch, stay at 2.")
    with text:
        if tip:
            for c in tip["cues"]:
                st.markdown(f"- {c}")
            st.caption(f"**Watch for:** {tip['watch']}")
            st.caption(f"**You should feel it in:** {tip['feel']}")
            st.caption(f"**Too hard?** {tip['easier']}")
        elif ex and ex.get("instructions"):
            for i, step in enumerate(ex["instructions"][:5], 1):
                st.markdown(f"{i}. {step}")
        else:
            st.caption("No tips for this one yet.")
    st.caption("General coaching tips, not medical advice. Stop if something hurts.")

