"""Read research.json: the evidence behind what the app recommends."""
import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).parent / "research.json"


@lru_cache(maxsize=1)
def entries():
    return {e["id"]: e for e in json.loads(PATH.read_text())["entries"]}


def get(entry_id):
    return entries().get(entry_id)


def why(entry_id):
    """A short 'why' line with a link, or '' when the claim has no verified source."""
    e = get(entry_id)
    if not e or not e.get("source") or e.get("status") == "unverified":
        return ""
    return f"{e['claim']} ([source]({e['source']}))"


def do(entry_id):
    """What to actually do, with the link: 'Train each muscle on 2 days a week... ([why](url))'.
    Falls back to the finding itself when an entry has no action written yet. '' if not verified."""
    e = get(entry_id)
    if not e or not e.get("source") or e.get("status") == "unverified":
        return ""
    return f"{e.get('action') or e['claim']} ([why]({e['source']}))"
