"""Exercise database access for the app (data sync lives in exercise_sync.py).

The upstream database only ships still photos (usually two per exercise: start
and end position), so we download them on first view and stitch them into a
small looping GIF.
"""
from concurrent.futures import ThreadPoolExecutor

import requests
import streamlit as st
from PIL import Image

import config
import exercise_sync


@st.cache_data(show_spinner="Downloading the exercise database (first run only)...")
def load_exercises():
    import json

    if not config.EXERCISES_JSON_PATH.exists():
        exercise_sync.check_for_updates(timeout=30)
    base = json.loads(config.EXERCISES_JSON_PATH.read_text())
    have = {e["name"] for e in base}
    return base + [e for e in extra_exercises() if e["name"] not in have]


EXTRA_PATH = config.BASE_DIR / "extra_exercises.json"  # open-licensed demos the main database lacks (see credit)
BUNDLED_DIR = config.BASE_DIR / "static"  # their photos ship with the app, e.g. static/wger/...


def extra_exercises():
    import json

    return json.loads(EXTRA_PATH.read_text()) if EXTRA_PATH.exists() else []


def credits():
    """Who made each bundled demo, for the Credits screen (CC-BY-SA asks for author, license and changes)."""
    return [(e["name"], e["credit"]) for e in extra_exercises() if e.get("credit")]


def credits_text():
    """One line per bundled demo: 'Pike Push-Up drawing: wger.de contributors (wger.de), CC-BY-SA 4.0, split ...'."""
    return " ".join(
        f"{name} drawing: {c['author']} ([{c['source']}]({c['url']})), "
        f"[{c['license']}]({c['license_url']}), {c['changes'].lower()}."
        for name, c in credits())


@st.cache_data
def _by_name():
    return {e["name"]: e for e in load_exercises()}


def find_exercise(name):
    return custom_by_name().get(name) or _by_name().get(name)


# --- exercises people create themselves ---------------------------------------------------------------
# Kept in that person's own settings (their database or their Google Drive), never in a shared file.
# homepage.py loads them into the session once per run (set_custom); photos are shown as data: URLs, so they are
# never served from a public address.
def set_custom(items):
    st.session_state["_custom_ex"] = {e["name"]: e for e in (items or [])}


def custom_by_name():
    try:
        return st.session_state.get("_custom_ex") or {}
    except Exception:  # outside a Streamlit run (tests)
        return {}


def custom_list():
    return list(custom_by_name().values())


def _custom_holds():
    return {n for n, e in custom_by_name().items() if e.get("hold")}


import training as _training  # noqa: E402

_training.EXTRA_HOLDS = _custom_holds


def make_custom(name, muscle, equipment, hold, steps, photos):
    """A custom exercise in the same shape as the database's. photos: up to two images (start, finish): uploaded
    files, or photos it already had (base64 text, when editing)."""
    import base64
    import io
    import re

    pics = []
    for f in photos[:2]:
        if isinstance(f, str):  # a photo it already had (stored as text)
            pics.append(f)
            continue
        img = Image.open(f).convert("RGB")
        img.thumbnail((480, 480))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=72)
        pics.append(base64.b64encode(buf.getvalue()).decode())
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "exercise"
    return {"name": name, "id": f"custom-{slug}", "custom": True, "hold": bool(hold),
            "primaryMuscles": [muscle] if muscle else [], "secondaryMuscles": [], "equipment": equipment or "body only",
            "category": "strength", "level": "beginner",
            "instructions": [x.strip() for x in steps.splitlines() if x.strip()], "photos": pics, "images": []}


def _custom_media(exercise, size=None, labels=False):
    """A data: URL for a custom exercise: its two photos as a moving demo (or one still), squared when size is set."""
    import base64
    import io

    pics = exercise.get("photos") or []
    if not pics:
        return None
    key = (exercise["id"], size, labels, len(pics))
    cache = st.session_state.setdefault("_custom_media", {})
    if key in cache:
        return cache[key]
    imgs = [Image.open(io.BytesIO(base64.b64decode(p))).convert("RGB") for p in pics]
    imgs = [_square(im, size) for im in imgs] if size else [im.resize(imgs[0].size) for im in imgs]
    buf = io.BytesIO()
    if len(imgs) == 2:
        frames = _loop(imgs[0], imgs[1], labels)
        frames[0].save(buf, "WEBP", save_all=True, append_images=frames[1:], duration=100, loop=0, quality=72)
    else:
        imgs[0].save(buf, "WEBP", quality=80)
    cache[key] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    return cache[key]


def update_database():
    """Check upstream for new exercises. Returns the sync result dict."""
    result = exercise_sync.check_for_updates(timeout=15)
    if result["status"] in ("updated", "downloaded"):
        load_exercises.clear()
        _by_name.clear()
    return result


ANIM_VERSION = "v3"  # bump to rebuild every animation (v2: clear holds, quick switch; v3: Start / Finish labels)


def _anim_path(exercise, labels=True):
    plain = "" if labels else "-plain"  # covers and banners: no Start / Finish pills
    return config.EXERCISES_DIR / exercise["id"] / f"{exercise['id']}-{ANIM_VERSION}{plain}.webp"


def has_demo(exercise):
    return _anim_path(exercise).exists()


def _local_image(rel_path):
    bundled = BUNDLED_DIR / rel_path
    if rel_path.startswith("wger/") and bundled.exists():
        return bundled
    path = config.EXERCISES_DIR / rel_path
    if not path.exists():
        r = requests.get(config.EXERCISE_IMAGES_URL + rel_path, timeout=30)
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return path


def static_url(path):
    """Browser URL for a file under ./static (served by Streamlit, cached by the browser)."""
    return "/app/static/" + str(path).split("/static/", 1)[1]


def _ease(t):
    return t * t * (3 - 2 * t)  # smoothstep: gentle start and finish, so the motion glides


def _crossfade_frames(a, b, steps=3):
    """A short blend between the two positions. Long blends showed both photos at once (a ghosted, blurry look),
    so the switch is quick and each position is held clearly instead."""
    return [Image.blend(a, b, _ease((i + 1) / (steps + 1))) for i in range(steps)]


def _label(img, text):
    """Burn a small pill ('1  Start') into the top-left corner, so anyone can tell which position is which."""
    from PIL import ImageDraw, ImageFont

    img = img.copy()
    size = max(12, round(img.width * 0.062))
    try:
        font = ImageFont.load_default(size=size)
    except (TypeError, OSError):  # very old Pillow: small bitmap font
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(img)
    pad, m = round(size * 0.55), round(size * 0.5)
    x0, y0, x1, y1 = draw.textbbox((0, 0), text, font=font)
    box = (m, m, m + (x1 - x0) + 2 * pad, m + (y1 - y0) + 2 * pad - round(size * 0.1))
    draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=(109, 40, 217))
    draw.text((m + pad - x0, m + pad - y0 - round(size * 0.05)), text, font=font, fill="white")
    return img


def _loop(a, b, labels=True):
    """Hold the start (~0.8 s), switch quickly, hold the finish (~0.8 s), switch back. Repeats forever (loop=0).
    Each held position wears its label ('1 Start', '2 Finish'); the quick blend between them has none."""
    if not labels:
        return [a] * 8 + _crossfade_frames(a, b) + [b] * 8 + _crossfade_frames(b, a)
    return [_label(a, "1  Start")] * 8 + _crossfade_frames(a, b) + [_label(b, "2  Finish")] * 8 + _crossfade_frames(b, a)


def exercise_gif(exercise, labels=True):
    if exercise and exercise.get("custom"):
        return _custom_media(exercise, labels=labels)
    return _exercise_gif(exercise, labels)


def _exercise_gif(exercise, labels=True):
    """Path to a smooth looping animation built from the exercise's photos, or None.

    The database only has still photos (start and end position). We blend between
    them with easing and hold briefly at each end, saved as animated WebP: much
    smoother and lighter than a two-frame GIF. (Name kept so callers don't change.)
    """
    path = _anim_path(exercise, labels)
    if path.exists():
        return str(path)
    try:
        photos = exercise.get("images") or []  # newly added exercises may have none yet
        if not photos:
            return None
        imgs = [Image.open(_local_image(p)).convert("RGB") for p in photos[:2]]
        width = min(420, imgs[0].width)
        imgs = [im.resize((width, round(im.height * width / im.width)), Image.LANCZOS) for im in imgs]
        imgs = [im.resize(imgs[0].size, Image.LANCZOS) for im in imgs]
        path.parent.mkdir(parents=True, exist_ok=True)
        if len(imgs) == 1:
            imgs[0].save(path, "WEBP", quality=82)
        else:
            a, b = imgs
            frames = _loop(a, b, labels)
            frames[0].save(path, "WEBP", save_all=True, append_images=frames[1:], duration=100, loop=0,
                           quality=78, method=4)
        return str(path)
    except (requests.RequestException, OSError):
        return None


def exercise_thumb(exercise):
    """Path to the exercise's first photo (a light static preview), or None."""
    try:
        photos = exercise.get("images") or []
        return str(_local_image(photos[0])) if photos else None
    except (requests.RequestException, OSError):
        return None


def _square(img, size):
    w, h = img.size
    s = min(w, h)
    left, top = (w - s) // 2, (h - s) // 2
    return img.crop((left, top, left + s, top + s)).resize((size, size), Image.LANCZOS)


def mini_url(exercise, animated=True, size=320):
    """URL of a small SQUARE image of the exercise, 4x sharper than it is shown (Streamlit's own
    st.image resizing makes small pictures soft). Animated = the smooth two-pose loop."""
    if not exercise:
        return None
    if exercise.get("custom"):
        return _custom_media(exercise, size=size)
    path = config.EXERCISES_DIR / exercise["id"] / f"{'anim' if animated else 'still'}{size}-{ANIM_VERSION}.webp"
    if not path.exists():
        try:
            photos = (exercise.get("images") or [])[:2]
            if not photos:
                return None
            imgs = [_square(Image.open(_local_image(p)).convert("RGB"), size) for p in photos]
            path.parent.mkdir(parents=True, exist_ok=True)
            if animated and len(imgs) == 2:
                a, b = imgs
                frames = _loop(a, b, labels=False)  # shown small: a label would be unreadable clutter
                frames[0].save(path, "WEBP", save_all=True, append_images=frames[1:], duration=100, loop=0, quality=78, method=4)
            else:
                imgs[0].save(path, "WEBP", quality=88)
        except (requests.RequestException, OSError):
            return None
    return static_url(path)


def thumb_url(exercise):
    """Browser URL of the first photo, or None (fetches it the first time)."""
    if exercise and exercise.get("custom"):
        return _custom_media(exercise, size=320)
    path = exercise_thumb(exercise)
    return static_url(path) if path else None


def anim_url(exercise, labels=True):
    path = exercise_gif(exercise, labels)
    if path and path.startswith("data:"):
        return path
    return static_url(path) if path else None


def prepare_minis(exercises, animated=True):
    """{name: url} for several exercises, built in parallel the first time."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(zip((x["name"] for x in exercises), pool.map(lambda x: mini_url(x, animated), exercises)))


def prepare_thumbs(exercises):
    """Fetch several preview photos in parallel; returns {name: path or None}."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(zip((e["name"] for e in exercises), pool.map(exercise_thumb, exercises)))


def prepare_demos(exercises, on_progress=None):
    """Download/build demos for several exercises at once (network bound, so a
    few threads make the first view much faster without loading the CPU)."""
    todo = [e for e in exercises if not has_demo(e)]
    if not todo:
        return
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, _ in enumerate(pool.map(exercise_gif, todo), 1):
            if on_progress:
                on_progress(i, len(todo))
