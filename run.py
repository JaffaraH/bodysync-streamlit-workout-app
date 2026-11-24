#!/usr/bin/env python3
"""One-command launcher for BodySync.

    python run.py                    # first run asks for your API keys, then starts the app
    python run.py --reconfigure      # change or add keys later
    python run.py --update-exercises # only refresh the exercise database, then exit
    python run.py --port 8600        # use a different port

Keys are saved to a local, git-ignored `.env` file. Every key is optional;
press Enter to skip one and that feature will simply show a hint in the app.
"""
import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ENV_PATH = BASE / ".env"

# (variable, what it unlocks, where to get it)
KEYS = [
    ("GEMINI_API_KEY", "AI workout plans, AI meal plans and the gym machine guide",
     "free key: https://aistudio.google.com/apikey"),
    ("EDAMAM_APP_ID", "recipe search (app id)", "free: https://developer.edamam.com/ (Recipe Search API)"),
    ("EDAMAM_APP_KEY", "recipe search (app key)", "same Edamam page as the app id"),
]


def read_env():
    values = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip("'\"")
    return values


def write_env(values):
    ENV_PATH.write_text("".join(f"{k}={v}\n" for k, v in values.items()))
    try:
        ENV_PATH.chmod(0o600)  # keys readable by you only
    except OSError:
        pass


def ensure_dependencies():
    try:
        import streamlit  # noqa: F401
        import google.genai  # noqa: F401
        import dotenv  # noqa: F401
        import PIL  # noqa: F401
        import requests  # noqa: F401
        return
    except ImportError:
        pass
    print("Some required packages are missing.")
    if sys.prefix == sys.base_prefix:
        print("Tip: use a virtual environment first:  python3 -m venv .venv && source .venv/bin/activate")
    if input("Install them now with pip? [Y/n] ").strip().lower() in ("", "y", "yes"):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(BASE / "requirements.txt")])
    else:
        sys.exit("Run: pip install -r requirements.txt")


def configure(args):
    env = read_env()
    # Flags and exported env vars win over prompts (handy for scripts/CI).
    provided = {
        "GEMINI_API_KEY": args.gemini_key or os.getenv("GEMINI_API_KEY"),
        "EDAMAM_APP_ID": args.edamam_app_id or os.getenv("EDAMAM_APP_ID"),
        "EDAMAM_APP_KEY": args.edamam_app_key or os.getenv("EDAMAM_APP_KEY"),
    }
    changed = False
    first_run = not env.get("BODYSYNC_SETUP_DONE") and not args.reconfigure
    interactive = sys.stdin.isatty()

    for var, unlocks, where in KEYS:
        if provided.get(var):
            env[var] = provided[var]
            changed = True
        elif (first_run or args.reconfigure) and interactive:
            if first_run and var == KEYS[0][0]:
                print("\nBodySync setup - all keys are optional, press Enter to skip.\n")
            hint = " (press Enter to keep current)" if env.get(var) else ""
            value = getpass.getpass(f"{var} - {unlocks}\n  [{where}]{hint}\n  > ").strip()
            if value:
                env[var] = value
                changed = True

    if not env.get("BODYSYNC_SETUP_DONE") and interactive:
        env["BODYSYNC_SETUP_DONE"] = "1"
        changed = True
    if changed:
        write_env(env)
        print(f"\nSaved settings to {ENV_PATH.name}\n")
    return env


def sync_exercises(quiet=False):
    """Fetch the exercise database, or pick up exercises added upstream."""
    sys.path.insert(0, str(BASE))
    import exercise_sync

    result = exercise_sync.check_for_updates(timeout=8)
    status = result["status"]
    if status == "downloaded":
        print(f"Downloaded the exercise database ({result['total']} exercises).")
    elif status == "updated":
        added = result["added"]
        print(f"Exercise database updated: {len(added)} new exercise(s)"
              + (f" ({', '.join(added[:5])}{'...' if len(added) > 5 else ''})." if added else "."))
    elif status == "offline" and not exercise_sync.config.EXERCISES_JSON_PATH.exists():
        print("Couldn't download the exercise database (offline?). The app will retry when you open Workouts.")
    elif not quiet:
        print("Exercise database is up to date.")


def main():
    p = argparse.ArgumentParser(description="Run BodySync locally.")
    p.add_argument("--reconfigure", action="store_true", help="re-enter or change API keys")
    p.add_argument("--update-exercises", action="store_true", help="refresh the exercise database and exit")
    p.add_argument("--port", default="8501")
    p.add_argument("--gemini-key", help="Gemini API key (prefer the prompt: flags land in shell history)")
    p.add_argument("--edamam-app-id")
    p.add_argument("--edamam-app-key")
    args = p.parse_args()

    ensure_dependencies()
    if args.update_exercises:
        sync_exercises()
        return
    env = configure(args)
    sync_exercises(quiet=True)

    cmd = [sys.executable, "-m", "streamlit", "run", str(BASE / "homepage.py"), "--server.port", str(args.port)]
    print(f"Starting BodySync on http://localhost:{args.port}  (Ctrl+C to stop)")
    try:
        sys.exit(subprocess.call(cmd, env={**os.environ, **env}, cwd=BASE))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
