"""Keeps the local copy of the Free Exercise DB in sync with the upstream repo.

No Streamlit imports, so run.py can call it at startup. A conditional request
(ETag) is used, so when nothing changed upstream this costs a few hundred bytes.
New exercises' photos are fetched on demand the first time they are viewed.
"""
import json
import time

import requests

import config


def _read_meta():
    try:
        return json.loads(config.EXERCISES_META_PATH.read_text())
    except (OSError, ValueError):
        return {}


def _names(path):
    try:
        return {e["name"] for e in json.loads(path.read_text())}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def check_for_updates(timeout=8):
    """Download exercises.json if missing or changed upstream.

    Returns {"status": "current" | "downloaded" | "updated" | "offline",
             "added": [names of new exercises], "total": int | None}
    """
    path = config.EXERCISES_JSON_PATH
    meta = _read_meta()
    headers = {"If-None-Match": meta["etag"]} if path.exists() and meta.get("etag") else {}
    try:
        r = requests.get(config.EXERCISES_JSON_URL, headers=headers, timeout=timeout)
        if r.status_code == 304:
            meta["checked_at"] = time.time()
            config.EXERCISES_META_PATH.write_text(json.dumps(meta))
            return {"status": "current", "added": [], "total": meta.get("total")}
        r.raise_for_status()
        data = json.loads(r.content)
        if not isinstance(data, list) or not data:
            raise ValueError("unexpected exercises.json content")
    except (requests.RequestException, ValueError):
        return {"status": "offline", "added": [], "total": meta.get("total")}

    old = _names(path)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(r.content)
    tmp.replace(path)  # atomic: a crash never leaves a half-written file
    config.EXERCISES_META_PATH.write_text(
        json.dumps({"etag": r.headers.get("ETag"), "checked_at": time.time(), "total": len(data)})
    )
    return {
        "status": "updated" if old else "downloaded",
        "added": sorted({e["name"] for e in data} - old) if old else [],
        "total": len(data),
    }
