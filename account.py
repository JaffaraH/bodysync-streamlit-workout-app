"""Profile: what you're here for, and a few optional details. Every answer says what it changes."""
import streamlit as st

import auth
import session_data
import ui
from exercise_data import credits_text

LEVELS = ["Beginner", "Intermediate", "Advanced"]
FOCUS = {"strength": "Get stronger", "skills": "Learn a skill", "explore": "Just look around"}
IMPERIAL, METRIC = "Imperial (lb, ft/in)", "Metric (kg, cm)"
LB_PER_KG, CM_PER_FT = 2.20462, 30.48
DRAFT_KEYS = ("pf_age", "pf_w_imp", "pf_w_met", "pf_ft", "pf_in", "pf_cm", "pf_level", "pf_units")


def _save_focus(username):
    label = st.session_state.get("pf_focus")
    key = next((k for k, v in FOCUS.items() if v == label), None)
    if key:
        session_data.save_settings(username, focus=key)
        st.toast("Home will put this first", icon=":material/check_circle:")


def _save_goal(username):
    session_data.save_settings(username, weekly_goal=int(st.session_state["pf_goal"]))
    st.toast("Weekly goal updated", icon=":material/check_circle:")


def profile_page(username, pages):
    ui.keep(*DRAFT_KEYS)
    st.title("You")
    st.caption("Everything here is optional except your fitness level. Each answer says what it changes.")
    with st.container(key="bs-more"):  # phone only: the places that don't fit in the tab bar
        st.markdown("##### More in BodySync")
        for k in ("progress", "workouts", "nutrition", "fitbuddy"):
            st.page_link(pages[k])
        st.divider()

    settings = session_data.settings(username)
    p = session_data.profile(username) or {}

    # ---- you steer ---------------------------------------------------------------------------
    st.subheader("Your focus", anchor=False)
    current = FOCUS.get(settings.get("focus"), None)
    st.segmented_control("What are you here for?", list(FOCUS.values()), default=current, key="pf_focus",
                         on_change=_save_focus, args=(username,))
    st.caption("Changes what Home shows first. Switch any time; nothing you've logged is affected.")
    st.slider("Training days per week", 1, 7, int(settings.get("weekly_goal", 3)), key="pf_goal",
              on_change=_save_goal, args=(username,))
    st.caption("Sets the goal on your Home flames. Missing a week costs you nothing.")
    st.toggle("Sounds", value=bool(settings.get("sound", True)), key="pf_sound",
              on_change=lambda: session_data.save_settings(username, sound=bool(st.session_state["pf_sound"])))
    st.caption("A soft chime when your rest is over, so you can look away while you rest.")
    import config
    if config.GIPHY_API_KEY:
        st.toggle("Fun GIFs", value=bool(settings.get("gifs", True)), key="pf_gifs",
                  on_change=lambda: session_data.save_settings(username, gifs=bool(st.session_state["pf_gifs"])))
        st.caption("A G-rated GIF while you rest and when you finish (from GIPHY).")

    # ---- about you ---------------------------------------------------------------------------
    st.subheader("About you", anchor=False)
    level = p.get("fitness_level")
    # a default only on first draw: after that the remembered value (ui.keep) is the widget's value
    first = {} if "pf_level" in st.session_state else {"index": LEVELS.index(level) if level in LEVELS else None}
    st.radio("Fitness level (required)", LEVELS, horizontal=True, key="pf_level", **first)
    st.caption("Why: hides exercises that are too advanced in the library, and tunes AI plans. Nothing else.")

    first = {} if "pf_units" in st.session_state else {"default": IMPERIAL}
    units = st.segmented_control("Units", [IMPERIAL, METRIC], key="pf_units", **first) or IMPERIAL
    metric = units == METRIC
    lb = float(p.get("weight") or 0) or None
    ft_total = float(p.get("height") or 0) or None
    feet = inches = None
    if ft_total:
        feet, inches = int(ft_total), round((ft_total - int(ft_total)) * 12)
        if inches == 12:
            feet, inches = feet + 1, 0

    age = st.number_input("Age (optional)", 13, 100, value=p.get("age") or None, placeholder="e.g. 25", step=1, key="pf_age")
    st.caption("Why: only used so the AI coach pitches plans at a suitable intensity. Skip it and nothing else changes.")

    if metric:
        weight = st.number_input("Weight in kg (optional)", 20.0, 300.0, key="pf_w_met", placeholder="e.g. 70",
                                 value=round(lb / LB_PER_KG, 1) if lb else None)
        cm = st.number_input("Height in cm (optional)", 100.0, 250.0, key="pf_cm", placeholder="e.g. 170",
                             value=float(round(ft_total * CM_PER_FT)) if ft_total else None)
    else:
        weight = st.number_input("Weight in lb (optional)", 40.0, 600.0, value=lb, placeholder="e.g. 150", key="pf_w_imp")
        c1, c2 = st.columns(2)
        ft_in = c1.number_input("Height, feet (optional)", 3, 8, value=feet, placeholder="ft", step=1, key="pf_ft")
        in_in = c2.number_input("inches", 0, 11, value=inches if feet else None, placeholder="in", step=1, key="pf_in")
    st.caption("Why: shows a rough BMI below and sizes AI meal plans. It is never used to choose your lifting weights.")

    st.caption("BodySync no longer stores free-text health notes. Areas to go easy on are set with simple choices at setup.")

    if st.button("Save profile", type="primary", icon=":material/check:", key="pf_save"):
        if not st.session_state.get("pf_level"):
            st.error("Pick your fitness level (the one required answer). Everything you typed is kept.")
        else:
            if metric:
                weight_lb = weight * LB_PER_KG if weight else None
                height_ft = (cm / CM_PER_FT) if cm else None
            else:
                weight_lb = weight if weight else None
                height_ft = (ft_in + (in_in or 0) / 12) if ft_in else None
            try:
                with st.spinner("Saving..."):
                    session_data.save_profile(
                        username, int(age) if age else None, weight_lb, height_ft, st.session_state["pf_level"], ""
                    )  # health_condition is no longer collected (and saving clears any old text)
                st.toast("Profile saved", icon=":material/check_circle:")
            except Exception as e:
                st.error(f"Couldn't save your profile ({type(e).__name__}). Your answers are still here, so try again.")

    saved = session_data.profile(username)
    if saved and saved.get("weight") and saved.get("height"):
        bmi = 703 * float(saved["weight"]) / ((float(saved["height"]) * 12) ** 2)
        st.metric("BMI", f"{bmi:.1f}", help="A rough guide that ignores muscle mass. Not used for any recommendation.")
    st.subheader("Look around", anchor=False)
    st.caption("See the first-run screens again. Nothing you've logged is changed.")
    a, b = st.columns(2)
    if a.button("Replay onboarding", icon=":material/replay:", key="pf_replay", width="stretch"):
        st.session_state.update(ob_replay=True, ob_step=0, ob_data={"days": int(settings.get("weekly_goal", 3))})
        st.switch_page(pages["home"])
    st.subheader("Account", anchor=False)
    if auth.mode() == "google":
        st.caption(f"Signed in with Google as **{username}**. Your workouts are saved in your own Google Drive.")
    elif auth.profiles_enabled():
        st.caption(f"Test account **{username}**, saved on this computer.")
    if auth.mode() == "google" or auth.profiles_enabled():
        if st.button("Sign out", icon=":material/logout:", key="pf_signout"):
            session_data.clear()
            st.session_state.clear()
            st.logout() if auth.mode() == "google" else st.rerun()
    else:
        st.caption("Saved on this device. No account needed.")
    st.subheader("About", anchor=False)
    st.caption(
        "Exercise photos: the public-domain [Free Exercise DB](https://github.com/yuhonas/free-exercise-db). "
        "Celebration flame: [Noto Emoji](https://github.com/googlefonts/noto-emoji) by Google, "
        "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), recoloured. "
        + ui.ART_CREDIT + ". " + credits_text()
    )
    ui.remember(*DRAFT_KEYS)
