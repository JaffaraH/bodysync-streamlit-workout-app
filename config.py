"""BodySync configuration.

Everything is read from environment variables, loaded from a local `.env` file
if one exists. `python run.py` creates that file for you; see `.env.example`.
Every key is optional: the app starts without them and the matching feature
shows a hint instead.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv not installed yet (run.py handles that)
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if load_dotenv:
    load_dotenv(ENV_PATH)

def _env(*names, default=""):
    """Setting from the environment/.env, falling back to Streamlit secrets
    (that's where a hosted copy, e.g. on Streamlit Community Cloud, keeps them)."""
    for name in names:
        if os.getenv(name):
            return os.getenv(name)
    try:
        import streamlit as st

        for name in names:
            if name in st.secrets:
                return str(st.secrets[name])
    except Exception:  # no secrets file, or running outside Streamlit
        pass
    return default


# --- Google Gemini (FitBuddy AI, AI meal plans, gym machine guide) ----------
# On a shared/hosted copy leave this empty: each person pastes their own free key in the app.
GEMINI_API_KEY = _env("GEMINI_API_KEY", "API_KEY")
# Flash-Lite has the most generous free quota; set GEMINI_MODEL to try a bigger model.
GEMINI_MODEL = _env("GEMINI_MODEL", default="gemini-2.5-flash-lite")

# --- Edamam (recipe search) -------------------------------------------------
EDAMAM_APP_ID = _env("EDAMAM_APP_ID", "app_id")
EDAMAM_APP_KEY = _env("EDAMAM_APP_KEY", "api_key_n")

# --- Database ---------------------------------------------------------------
# "sqlite"   (default): a local file, nothing to set up.
# "bigquery": the original cloud database. Needs `pip install -r
#             requirements-bigquery.txt`, GCP_PROJECT_ID and Google credentials
#             (GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json).
# "drive": Sign in with Google and save into the person's own Google Drive (no database, no accounts for
#          you to manage). Switched on automatically when an [auth] section exists in Streamlit secrets.
def _auth_configured():
    try:
        import streamlit as st

        return "auth" in st.secrets and "client_id" in st.secrets["auth"]
    except Exception:  # no secrets file, or running outside Streamlit
        return False


AUTH_CONFIGURED = _auth_configured()
# "postgres": any hosted Postgres (Neon, Supabase, ...): just set DATABASE_URL, it is picked automatically.
DATABASE_URL = _env("DATABASE_URL")
DB_BACKEND = _env(
    "BODYSYNC_DB", default="drive" if AUTH_CONFIGURED else ("postgres" if DATABASE_URL else "sqlite")
).lower()
GCP_PROJECT_ID = _env("GCP_PROJECT_ID", "PROJECT_ID")
BQ_DATASET = _env("BQ_DATASET", default="bodysyncusers")

# --- GIPHY (fun G-rated GIFs between sets and at the finish; optional) -----------------------------
# One free key for the whole app from https://developers.giphy.com/ (kept on the server, never in the browser).
GIPHY_API_KEY = _env("GIPHY_API_KEY")

# --- Local storage ----------------------------------------------------------
DATA_DIR = Path(os.getenv("BODYSYNC_DATA_DIR", BASE_DIR / "data"))
DB_PATH = Path(os.getenv("BODYSYNC_DB_PATH", DATA_DIR / "bodysync.db"))
EXERCISES_DIR = BASE_DIR / "static" / "exercises"  # served to the browser at /app/static/exercises/
EXERCISES_JSON_PATH = DATA_DIR / "exercises.json"
EXERCISES_META_PATH = DATA_DIR / "exercises.meta.json"

# Free Exercise DB (https://github.com/yuhonas/free-exercise-db)
EXERCISES_JSON_URL = (
    "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
)
EXERCISE_IMAGES_URL = (
    "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/"
)

LOGO_PATH = BASE_DIR / "static" / "logo.svg"  # crisp vector, also served at /app/static/logo.svg
