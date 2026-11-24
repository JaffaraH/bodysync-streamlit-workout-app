"""Storage facade. The rest of the app only imports `db`; which backend answers
is chosen in config.py: "sqlite" (default), "postgres" (when DATABASE_URL is set)
or "bigquery" (BODYSYNC_DB=bigquery)."""
import config

if config.DB_BACKEND == "drive":
    from db_drive import *  # noqa: F401,F403
elif config.DB_BACKEND == "postgres":
    from db_postgres import *  # noqa: F401,F403
elif config.DB_BACKEND == "bigquery":
    from db_bigquery import *  # noqa: F401,F403
else:
    from db_sqlite import *  # noqa: F401,F403
