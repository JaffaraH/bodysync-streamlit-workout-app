# How BodySync is built

This guide is for developers who want to understand the code, change it, or build something similar. It assumes
you know Python and have run a "hello world" Streamlit app. Everything else is explained here.

## The one idea to understand first: Streamlit reruns the whole script

A Streamlit app is a Python script that runs **top to bottom on every tap**. There is no event loop to write and no
frontend code. When someone taps a button, Streamlit reruns the script, and that run's `st.button(...)` returns
`True`. Three consequences shape the whole codebase:

1. **Anything that must survive a tap lives in `st.session_state`** (a dict kept per browser tab). Which step of a
   flow you're on, the exercises you picked, the workout in progress: all of it is session state.
2. **Reading from storage on every tap would be slow**, so `session_data.py` keeps a per-session copy and refreshes
   it right after each write.
3. **A page is a function.** `homepage.py` calls the right page function, and that function draws whatever the
   current session state says to draw.

## Files at a glance

| Layer | Files | What they do |
|---|---|---|
| **Entry point** | `homepage.py` | Runs on every tap: picks sign-in or the app, builds the page list, runs the current page, draws the tab bar |
| **Who is signed in** | `auth.py` | Local mode (your computer), Google mode (`st.login`), and the public-address safety check |
| **Pages** (one function each) | `home.py`, `today.py` (Workouts), `lifts.py` (Library), `skills.py`, `progress.py`, `account.py` (You), `workouts.py` (Exercise library), `nutrition.py`, `chat.py` (FitBuddy AI), `onboarding.py` | Draw a screen from session state; never talk to storage directly |
| **Flows used by several pages** | `playlist_builder.py`, `exercise_picker.py` (search, filters, create your own, swap), `plan.py` (Plan my week), `formtips.py` (How to do it), `celebration.py`, `gifs.py` (encouragement and G-rated GIFs) | Multi-step flows and shared pickers |
| **Rules (no Streamlit inside)** | `training.py`, `skills_logic.py`, `protein.py` (maths part), `research.py`, `targets.py`, `body_map.py` | Progressive overload, PR detection, skill ladders, protein targets, citations, what each move works and the feeling-stuck check. Plain functions, unit-tested |
| **Data** | `session_data.py` → `db.py` → `db_sqlite.py` / `db_drive.py` / `db_postgres.py` / `db_bigquery.py` | A per-session cache over one storage interface with four backends |
| **Exercise content** | `exercise_data.py`, `exercise_sync.py`, `extra_exercises.json`, `curated_workouts.json`, `move_targets.json`, `progressions.json`, `form_cues.json`, `research.json` | The open exercise database, animated demos, curated workouts, skill ladders and sources |
| **Look and feel** | `ui.py`, `.streamlit/config.toml` | Theme, shared components (tap rows, tiles, hero, tab bar, demo), and the CSS that makes Streamlit feel like a phone app |
| **Settings** | `config.py`, `run.py` | Reads keys from `.env` / Streamlit secrets; `run.py` is the friendly launcher |

The rule that keeps this readable: **pages call flows and rules; flows and rules call `session_data`; only
`session_data` calls `db`.** Nothing in `training.py` imports Streamlit, which is why it can be tested with plain
`python tests/test_training.py`.

## One tap, start to finish

`homepage.main()` runs on every tap, in this order:

1. **`auth.mode()`** returns `"google"` if `.streamlit/secrets.toml` has an `[auth]` section, otherwise `"local"`.
2. **`auth.on_private_network()`** (local mode only) returns `True` on localhost or a home network. On a public
   address it returns `False`, and `main()` shows `auth.setup_needed` instead of the app, because a public copy
   without sign-in would give every visitor the same account.
3. **`auth.signed_in()`** returns whether someone is signed in. If not, `main()` shows the sign-in page
   (`auth.landing`, whose button calls `st.login`) and stops.
4. **`auth.identity()`** returns `(username, display name)`. In Google mode, the username is the person's email from
   `st.user`; it becomes the key for all of their data.
5. **`session_data.load_live(username)`** brings back a workout left unfinished (saved after every set), so a phone
   that slept or a refreshed page loses nothing.
6. **`st.navigation(pages, position="hidden").run()`** runs the current page function. The menu is hidden because
   BodySync draws its own phone tab bar.
7. **`ui.play_pending()`** does one-off browser actions requested during the run: the end-of-rest chime, and
   scrolling to the top when a flow moved to a new step.
8. **`ui.tab_bar()`** and **`ui.continue_bar()`** draw the bottom bar and, if a workout is in progress, the
   "Continue workout" strip.
9. **`_flush()`** saves to Google Drive once, at the end, however many changes the run made (Drive mode only).

## Following one workout through the code

Here is what happens from tapping the *Strong knees* tile to the set being saved.

**1. The tile.** `today.day_view()` draws the Workouts page. `today._tile_row()` draws each row of tiles; each tile
is an `st.button` stretched invisibly over a picture (`TILE_CSS`). Tapping it calls `today._open_tpl("strong-knees")`,
which sets `t_phase = "template"` in session state. The next run, `today.today_page()` reads `t_phase` and calls
`template_view()`.

**2. The preview.** `today.template_view()` reads the workout from `curated_workouts.json` (via `today.curated()`)
and shows its Goal card (`_goal_card`) and the sources from `research.json` (via `research.get`). *Start this
workout* calls `today._start_template(username, w)`, which turns the workout's exercises into a template
(`{name: {sets, rep_low, rep_high, hold}}`) and calls `today._begin()`.

**3. Building today's plan.** `today._begin(username, names)`:
- calls `today._make_items(username, names)`, which calls `today._plan()`. For each exercise, `_plan` looks up your
  history (`session_data.all_sets`), then asks **`training.suggest(lift, history, days_off, unit)`**, which returns
  `{"weight", "reps", "sets", "tag", "reason"}`: your next target, using double progression.
- stores the workout as `st.session_state["sess"]` with `ready=True` and `started=None` (the clock hasn't started).
- calls `session_data.save_live()` so the workout survives a reload.

**4. The ready page.** `today.session_view()` sees `sess["ready"]` and calls `_ready_view()`. It shows the warm-up
offer (`_phase_offer`) and the editable plan (`_plan_editor`), where the up and down arrows call `_move`, the X calls
`_remove`, and *Add exercises* opens `_add_dialog`. That dialog uses the same `exercise_picker.search()` as New
playlist. *Start workout* sets `started` to now and `ready=False`.

**5. A set.** `session_view()` now calls `_set_panel(sess, item)`. It shows the moving demo (`ui.demo` of
`exercise_data.anim_url`), the reps (and weight) inputs, and *Done with set 1*, which calls **`today._done_set()`**.
That function marks the row done, checks for a record with `training.PRTracker`, and starts the rest timer
(`sess["rest"]`). The next run shows `_rest_panel()`; a fragment with `run_every=1` counts it down and calls
`ui.ping()` at zero.

**6. Finishing.** *Finish workout* calls **`today._finish(username, sess)`**, which:
- splits done sets into lifts, holds, warm-ups (logged as stretching) and skill parts (logged as skill practice),
- writes them with `session_data.log_sets()`, which calls `db.log_sets()` in whichever backend is active,
- updates your best set per lift (`session_data.upsert_lift`) so the next suggestion starts from it,
- saves the workout's name (`session_titles`) so Progress can count your favourites,
- returns a summary that `today.celebrate()` shows.

**7. Progress.** `progress.progress_page()` reads the same sets back (`session_data.all_sets`, which leaves out
workouts you removed) and computes everything on the fly: `week_streak`, `totals`, `favourites`, `to_improve`,
`chart_section`. Nothing is stored twice, so the numbers can't drift.

## Storage: one interface, four backends

`db.py` is a few lines: it imports one backend based on `config.DB_BACKEND`. Every backend provides the same
functions (`list_sets`, `log_sets`, `get_pref`, `set_pref`, `list_routines`, ...), and
`tests/test_db_contract.py` checks they behave the same (SQLite always; Postgres too when `TEST_DATABASE_URL` is set).

| Backend | When it's used | Where data lives |
|---|---|---|
| `db_sqlite.py` | Default on your computer | `data/bodysync.db` |
| `db_drive.py` | When Google sign-in is set up | One private JSON file per person, in **their own** Google Drive app folder |
| `db_postgres.py` | When `DATABASE_URL` is set | Your own Postgres (for example Neon or Supabase) |
| `db_bigquery.py` | `BODYSYNC_DB=bigquery` | The original team's BigQuery dataset |

Small settings (week plan, saved feelings, protein foods, removed workouts) live as one JSON blob in the
preferences table (`session_data.settings` / `save_settings`), so adding a setting never needs a schema change.

## Exercise content and demos

- **`exercise_data.load_exercises()`** downloads the [Free Exercise DB](https://github.com/yuhonas/free-exercise-db)
  once (cached with `st.cache_data`) and adds `extra_exercises.json` (open-licensed demos it lacks).
- Every exercise there has exactly **two photos**: a start and an end. **`exercise_data.exercise_gif()`** turns them
  into a looping animated WebP: hold the start (labelled "1 Start"), blend quickly, hold the finish ("2 Finish").
  `mini_url()` makes small square versions without labels for lists. Bump `ANIM_VERSION` to rebuild them all.
- Moves two photos can't show (circles, flutters) get a plain note and their written steps (`formtips.motion_note`).
- **Your own exercises** (`exercise_data.make_custom`) live in that person's settings, with up to two photos stored
  as text. `homepage.py` loads them each run with `exercise_data.set_custom`, so `find_exercise`, the picker and every
  list see them; their demos are built as `data:` URLs, so they're never served from a public address.

## The research rule

Any sentence in the app that states a fact about training comes from `research.json`, through
`research.why(id)`, which returns the claim plus a link, or nothing if the entry isn't verified. Unverified claims
are never shown. What each move works (area and job) and the "For your goal" notes live in `move_targets.json`;
`tests/test_targets.py` checks every curated move is described and every id it cites is verified. `tests/test_research.py` checks every entry is complete and that only entries with a source can be
shown.

## Patterns worth copying

- **Flows keep their own state.** `playlist_builder.py` keeps everything in one dict (`st.session_state["pb"]`)
  because widget values vanish when a step stops drawing them.
- **Tap anywhere on a row.** `ui.tap_row()` draws a picture and text, then lays an invisible `st.button` over the whole
  row with CSS. It returns `(opened, acted)`.
- **Pinned main action.** Any screen's primary button goes in `st.container(key="bs-donebar")`, which sticks it to
  the bottom of the screen.
- **Callbacks for state changes.** `on_click=` callbacks run before the rerun, so the new state is already in place
  when the page draws. This also keeps dialogs open.

## Where to look when something breaks

| Symptom | Look at |
|---|---|
| A tap does nothing | The overlay CSS in `ui.TAP_CSS` or `today.TILE_CSS` |
| A demo doesn't move | It was drawn with `st.image`; use `ui.demo` |
| A suggestion seems wrong | `training.suggest` and `tests/test_training.py` |
| Data didn't save on the hosted copy | `homepage._flush` and `db_drive.py` (the Google token lasts about an hour) |
| A page opens half-way down | Call `ui.to_top()` when the flow changes step |
