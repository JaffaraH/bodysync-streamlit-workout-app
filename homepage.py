# Entry point: `python run.py` (or `streamlit run homepage.py`)
import streamlit as st

import auth
import exercise_data
import config
import db
import session_data
import ui
from account import profile_page
from chat import chat_page
from home import home_page
from lifts import lifts_page
from nutrition import nutrition_page
from progress import progress_page
from skills import skills_page
from today import today_page
from workouts import workouts_page

st.set_page_config(page_title="BodySync", page_icon=":material/fitness_center:", layout="centered", initial_sidebar_state="auto")
ui.inject_css()

try:  # only exists in Google/Drive mode
    from db_drive import DriveAuthError
except Exception:  # pragma: no cover
    class DriveAuthError(Exception):
        pass


def _flush():
    """Upload any changes to the person's Drive once per run (no-op for the local file)."""
    flush = getattr(db, "flush", None)
    if not flush:
        return
    try:
        flush()
    except DriveAuthError:
        auth.reconnect_notice(st.login)
    except Exception as e:
        st.toast(f"Couldn't save just now ({type(e).__name__}). We'll try again on your next tap.", icon=":material/warning:")


def main():
    if st.query_params.get("preview") == "signin":  # lets you see the sign-in page without signing out
        st.navigation(
            [st.Page(lambda: auth.landing(lambda: st.query_params.clear()), title="Sign in", url_path="signin")],
            position="hidden",
        ).run()
        return
    if auth.mode() == "local" and not auth.on_private_network():  # never one shared account on a public address
        st.navigation([st.Page(auth.setup_needed, title="Set up sign-in", url_path="setup")], position="hidden").run()
        return
    if not auth.signed_in():
        landing = auth.picker if auth.profiles_enabled() else (lambda: auth.landing(st.login))
        st.navigation([st.Page(landing, title="Sign in", url_path="signin")], position="hidden").run()
        return

    username, display = auth.identity()
    st.session_state.update(username=username, display=display, logged_in=True)
    exercise_data.set_custom(session_data.settings(username).get("custom_exercises"))  # your own exercises
    if "sess" not in st.session_state and not st.session_state.get("_live_checked"):
        st.session_state["_live_checked"] = True  # once per visit: bring back a workout left unfinished
        live = session_data.load_live(username)
        if live:
            st.session_state["sess"] = live
    pages = {}

    def home():
        home_page(username, pages)

    def workout():
        today_page(username, pages)

    def my_lifts():
        lifts_page(username, pages)

    def skills():
        skills_page(username, pages)

    def progress():
        progress_page(username, pages)

    def profile():
        profile_page(username, pages)

    def library():
        workouts_page(username, pages)

    def nutrition():
        nutrition_page(username, pages)

    def fitbuddy():
        chat_page(username, pages)

    pages.update(
        home=st.Page(home, title="Home", icon=":material/home:", url_path="home", default=True),
        workout=st.Page(workout, title="Workouts", icon=":material/fitness_center:", url_path="workout"),
        lifts=st.Page(my_lifts, title="Library", icon=":material/bookmarks:", url_path="lifts"),
        skills=st.Page(skills, title="Skills", icon=":material/trending_up:", url_path="skills"),
        progress=st.Page(progress, title="Progress", icon=":material/bar_chart:", url_path="progress"),
        workouts=st.Page(library, title="Exercise library", icon=":material/menu_book:", url_path="workouts"),
        nutrition=st.Page(nutrition, title="Nutrition", icon=":material/restaurant:", url_path="nutrition"),
        fitbuddy=st.Page(fitbuddy, title="FitBuddy AI", icon=":material/smart_toy:", url_path="fitbuddy"),
        profile=st.Page(profile, title="Profile", icon=":material/person:", url_path="profile"),
    )
    nav = st.navigation(list(pages.values()), position="hidden")  # we draw the menu ourselves (logo first)
    goto = st.session_state.pop("_goto", None)  # a page change asked for by a button, possibly inside a pop-up
    if goto in pages:
        st.switch_page(pages[goto])

    with st.sidebar:
        ui.logo_button(pages["home"])
        st.page_link(pages["home"])
        ui.nav_heading("Train")
        for key in ("workout", "lifts", "skills", "progress"):
            st.page_link(pages[key])
        ui.nav_heading("Explore")
        for key in ("workouts", "nutrition", "fitbuddy"):
            st.page_link(pages[key])
        ui.nav_heading("You")
        st.page_link(pages["profile"])
        st.divider()
        if auth.mode() == "google":
            st.caption(f"Signed in as **{username}**")
            if st.button("Sign out", icon=":material/logout:", type="tertiary"):
                session_data.clear()
                st.session_state.clear()
                st.logout()
        elif auth.profiles_enabled():
            st.caption(f"Signed in as **{username}** (saved on this device)")
            if st.button("Sign out", icon=":material/logout:", type="tertiary", key="local_signout"):
                session_data.clear()
                st.session_state.clear()
                st.rerun()
        else:
            st.caption("Saved on this device")

    st.session_state["_focus_mode"] = False  # pages that need the whole screen (onboarding, a live workout) set this
    here_now = nav.url_path
    st.session_state["_arrived"] = st.session_state.get("_here") != here_now  # opened from another page this run
    st.session_state["_here"] = here_now
    try:
        nav.run()
    except DriveAuthError:
        auth.reconnect_notice(st.login)
        return
    ui.play_pending(session_data.settings(username).get("sound", True))
    if not st.session_state.get("_focus_mode"):
        here = next((k for k, pg in pages.items() if pg.url_path == nav.url_path), None)
        here = "profile" if here in ("progress", "workouts", "nutrition", "fitbuddy") else here  # opened from You
        ui.tab_bar(pages, here)
        ui.continue_bar(pages, here)
    _flush()


main()
