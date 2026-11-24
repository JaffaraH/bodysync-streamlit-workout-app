"""Progress: what you've built and what to do next. Your weeks in a row (purple flame), lifetime totals from real
logged sets (they only go up), your favourites, the area that needs you most, one chart (all exercises by
default, or any one you pick), skill ladders, and your workout history (repeat it, put it on your week, remove it).

Three states: new ("your baseline starts today"), active, and returning after a break ("your baseline is
safe"). Estimated strength is kept apart from your real best and labelled as an estimate (Epley formula).
"""
import csv
import html
import io
from datetime import date, datetime

import altair as alt
import pandas as pd
import streamlit as st

import research
import session_data
import skills_logic as sk
import targets
import training
import ui
from exercise_data import find_exercise, mini_url

CSS = """<style>
.pg-stats { display: flex; gap: .5rem; margin: .6rem 0 .4rem; }
.pg-stat { flex: 1; min-width: 0; }
.pg-stat .n { font-size: 2.1rem; font-weight: 800; letter-spacing: -.03em; line-height: 1.05; font-variant-numeric: tabular-nums; white-space: nowrap; }
.pg-stat .l { font-size: .8rem; opacity: .65; margin-top: .15rem; }
.pg-stat .n.up { color: #0F766E; }
.pg-note { line-height: 1.55; margin: 0 0 .55rem; padding-left: .9rem; border-left: 3px solid rgba(139,92,246,.45); }
.pg-hello { padding: 1rem 1.1rem; border-radius: 16px; background: rgba(139,92,246,.10); line-height: 1.55; margin: 0 0 1.2rem; }
[class*='st-key-keep-hist-'] { padding: .45rem 0; border-bottom: 1px solid rgba(139,92,246,.14); }
@media (max-width: 640px) { .pg-stat .n { font-size: 1.3rem; } .pg-stats { gap: .8rem; } }
</style>"""
DARK_UP = "<style>.pg-stat .n.up { color: #4FD1C5; }</style>"


def _stats(items):
    """Big numbers in a row (no boxes). items = [(value, label, css_class)]."""
    st.html('<div class="pg-stats">' + "".join(
        f'<div class="pg-stat"><div class="n {c}">{html.escape(str(v))}</div><div class="l">{html.escape(l)}</div></div>'
        for v, l, c in items) + "</div>")


def _day(ts):
    return datetime.fromisoformat(ts).date()


def progress_page(username, pages):
    st.html(CSS + (DARK_UP if ui.is_dark() else ""))
    ui.back_to_you(pages)
    st.title("Progress")
    unit = session_data.unit(username)
    sets = session_data.all_sets(username)
    strength = training.strength_sets(sets)
    sessions = training.group_sessions(sets)

    if not sets:
        st.html('<div class="pg-hello"><b>Your baseline starts today.</b> Finish your first workout or skill practice and this '
                "page fills in: your best sets, a strength curve for each lift, and what we notice over time. "
                "Nothing here ever resets.</div>")
        a, b = st.columns(2)
        if a.button("Start a workout", type="primary", icon=":material/play_arrow:", width="stretch", key="pg_go"):
            ui.to_workout(pages)
        if b.button("Practise a skill", icon=":material/trending_up:", width="stretch", key="pg_sk"):
            st.switch_page(pages["skills"])
        return

    away = training.days_since(sessions[0]["performed_at"])
    if away >= 14:
        st.html(f'<div class="pg-hello"><b>Welcome back. Your baseline is safe.</b> Your last session was '
                f"{html.escape(training.break_label(away))}. Every record below is still yours, and your next workout eases you back in.</div>")

    hero(username, sets)
    totals(sets, sessions, unit)
    favourites(username, sessions)
    to_improve(username, pages, sets)
    chart_section(sets, strength, unit)
    notes(sets, strength, unit)
    if away < 14:  # a longer break gets the welcome-back note instead
        feeling_stuck(pages, sets, unit)
    skills_section(username, pages, sets)
    history(username, pages, sessions, unit)
    export(sets, unit)


# --- motivation: weeks in a row, this week's flames ------------------------------------------------
def week_streak(sets, goal, today=None):
    """Weeks in a row you reached your weekly goal. This week counts once it's reached, and never breaks the
    streak while it's still going."""
    today = today or date.today()
    monday = today.toordinal() - today.weekday()
    days = {_day(s["performed_at"]).toordinal() for s in sets}
    per_week = lambda start: sum(1 for d in days if start <= d < start + 7)
    streak = 1 if per_week(monday) >= goal else 0
    start = monday - 7
    while per_week(start) >= goal:
        streak += 1
        start -= 7
    return streak, per_week(monday)


def hero(username, sets):
    from celebration import FIRE

    goal = int(session_data.settings(username).get("weekly_goal", 3))
    streak, this_week = week_streak(sets, goal)
    left = max(0, goal - this_week)
    big = (f"{streak} week{'s' if streak != 1 else ''} in a row" if streak else "Start your streak this week")
    sub = (f"You've hit your goal of {goal} day{'s' if goal != 1 else ''} this week." if not left
           else f"{this_week} of {goal} days this week. {left} more to keep it going." if streak
           else f"{this_week} of {goal} days so far. Showing up {goal} times this week starts it.")
    st.html("<style>.pg-hero{display:flex;align-items:center;gap:14px;padding:14px 16px;border-radius:18px;"
            "background:var(--bs-accent-soft);margin:.2rem 0 .6rem}.pg-hero .f{width:58px;height:58px;flex:0 0 auto;"
            "background-size:contain;background-repeat:no-repeat;filter:hue-rotate(250deg) saturate(1.15)}"
            ".pg-hero .b{font-size:1.25rem;font-weight:800;letter-spacing:-.01em}.pg-hero .s{font-size:.9rem;opacity:.8}</style>"
            f'<div class="pg-hero"><div class="f" style="background-image:url(\'{FIRE}\')" aria-hidden="true"></div>'
            f'<div><div class="b">{html.escape(big)}</div><div class="s">{html.escape(sub)}</div></div></div>')
    ui.flames(training.week_dots(sets))


# --- lifetime totals: real logged sets only ------------------------------------------------------
def totals(sets, sessions, unit):
    holds = training.hold_names()
    lifted = sum(s["weight"] * s["reps"] for s in sets if s["weight"])
    reps = sum(s["reps"] for s in sets if s["exercise"] not in holds and s["day_type"] not in ("cardio",)
               and not s["exercise"].startswith("Walk: "))
    days = {_day(s["performed_at"]) for s in sets}
    st.subheader("Lifetime totals", anchor=False)
    _stats([(f"{len(sessions):,}", "workouts", ""), (f"{len(days):,}", "days trained", ""),
            (f"{sum(1 for s in sets if s['is_pr']):,}", "personal records", "")])
    _stats([(f"{len(sets):,}", "sets", ""), (f"{reps:,}", "reps", ""),
            (f"{round(training.to_unit(lifted, unit)):,} {unit}" if lifted else "Bodyweight", "total lifted", "")])
    st.caption("Counted from every set you logged. They only ever go up (unless you remove a workout).")


# --- favourites ------------------------------------------------------------------------------------
def _title(username, sess):
    titles = session_data.settings(username).get("session_titles") or {}
    return titles.get(sess["session_id"]) or training.DAY_LABELS.get(sess["day_type"], "Workout")


def favourites(username, sessions):
    counts = {}
    for sess in sessions:
        t = _title(username, sess)
        counts[t] = counts.get(t, 0) + 1
    ex_counts = {}
    for sess in sessions:
        for name in {x["exercise"] for x in sess["sets"] if not x["exercise"].startswith(("Skill: ", "Walk: "))}:
            ex_counts[name] = ex_counts.get(name, 0) + 1
    if not counts:
        return
    st.subheader("Your favourites", anchor=False)
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
    st.html("".join(f'<p class="pg-note"><b>{html.escape(t)}</b>, done {n} time{"s" if n != 1 else ""}</p>' for t, n in top))
    if ex_counts:
        most = sorted(ex_counts.items(), key=lambda kv: -kv[1])[:3]
        st.caption("Exercises you do most: " + ", ".join(f"{n} ({c}×)" for n, c in most))


# --- what to work on next ----------------------------------------------------------------------------
GROUPS = {"Chest": {"chest"}, "Back": {"lats", "middle back", "lower back", "traps"}, "Shoulders": {"shoulders"},
          "Arms": {"biceps", "triceps", "forearms"}, "Legs": {"quadriceps", "hamstrings", "calves", "adductors"},
          "Glutes": {"glutes", "abductors"}, "Core": {"abdominals"}}
GROUP_TAG = {"Chest": "push", "Back": "pull", "Shoulders": "shoulders", "Arms": "arms", "Legs": "legs",
             "Glutes": "glutes", "Core": "core"}


def to_improve(username, pages, sets):
    """The body area you trained least in the last 4 weeks, with one workout for it."""
    today = date.today()
    recent = [s for s in sets if (today - _day(s["performed_at"])).days < 28 and s["day_type"] not in ("stretch", "cardio")]
    if len(recent) < 6:
        return
    hits = {g: 0 for g in GROUPS}
    for s in recent:
        ex = find_exercise(s["exercise"].replace("Skill: ", ""))
        for m in (ex or {}).get("primaryMuscles") or []:
            for g, ms in GROUPS.items():
                if m in ms:
                    hits[g] += 1
    low = min(hits, key=lambda g: hits[g])
    if hits[low] > 0.6 * max(hits.values()):
        return  # nothing stands out: balanced enough
    import today as today_page

    tag = GROUP_TAG[low]
    w = next((x for x in today_page.curated() if x.get("tag") == tag or x["focus"] == tag), None)
    st.subheader("Room to grow", anchor=False)
    st.html(f'<p class="pg-note">{html.escape(low)} got the least work in the last 4 weeks '
            f'({hits[low]} set{"s" if hits[low] != 1 else ""}, versus {max(hits.values())} for your most-trained area).'
            + (f" Try <b>{html.escape(w['title'])}</b> next.</p>" if w else "</p>"))
    if w and st.button(f"Open {w['title']}", icon=":material/arrow_forward:", key="pg_grow"):
        st.session_state.update(t_phase="template", t_tpl=w["id"])
        ui.to_workout(pages)


# --- one chart: everything by default, or one exercise ------------------------------------------------
ALL = "All exercises"


def chart_section(sets, strength, unit):
    st.subheader("Over time", anchor=False)
    counts = {}
    for sess in training.group_sessions(strength):
        for name in {x["exercise"] for x in sess["sets"]}:
            counts[name] = counts.get(name, 0) + 1
    muscles = sorted({m for n in counts for m in ((find_exercise(n) or {}).get("primaryMuscles") or [])})
    c1, c2 = st.columns(2)
    muscle = c1.selectbox("Muscle", ["All muscles"] + muscles, key="pg_muscle",
                          format_func=lambda m: m if m == "All muscles" else m[:1].upper() + m[1:])
    names = sorted((n for n in counts if muscle == "All muscles" or muscle in ((find_exercise(n) or {}).get("primaryMuscles") or [])),
                   key=lambda n: (-counts[n], n))
    pick = c2.selectbox("Exercise", [ALL] + names, key="pg_lift2",
                        format_func=lambda n: n if n == ALL else f"{n} ({counts[n]}×)")
    color = "#A070F0" if ui.is_dark() else "#7C3AED"  # validated single-series colour for each theme
    if pick == ALL:
        today = date.today()
        start = today.toordinal() - today.weekday() - 7 * 11
        weeks = {start + 7 * i: 0 for i in range(12)}
        for s in sets:
            d = _day(s["performed_at"]).toordinal()
            wk = d - date.fromordinal(d).weekday()
            if wk in weeks:
                weeks[wk] += 1
        df = pd.DataFrame([{"Week": pd.to_datetime(date.fromordinal(k)), "Sets": v} for k, v in weeks.items()])
        chart = alt.Chart(df).mark_bar(color=color, cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=14).encode(
            x=alt.X("Week:T", title=None, axis=alt.Axis(format="%d %b", grid=False, labelAngle=0, tickCount=6)),
            y=alt.Y("Sets:Q", title="Sets per week", axis=alt.Axis(gridOpacity=.15, tickCount=4)),
            tooltip=[alt.Tooltip("Week:T", title="Week of", format="%d %b"), alt.Tooltip("Sets:Q")]).properties(height=220)
        st.altair_chart(chart.configure_view(strokeWidth=0).configure(background="transparent"), width="stretch", theme="streamlit")
        st.caption("Every set you logged, week by week, for the last 12 weeks. Pick an exercise to see its numbers.")
        return
    history = list(reversed(training.lift_history(strength, pick)))  # oldest first
    all_sets = [s for h in history for s in h["sets"]]
    best = max(all_sets, key=lambda s: (s["weight"], s["reps"]))
    first_top = max(s["weight"] for s in history[0]["sets"])
    last_top = max(s["weight"] for s in history[-1]["sets"])
    change = last_top - first_top
    change_txt = (f"+{training.fmt_weight(change, unit)}" if change > training.EPS else "Same" if abs(change) <= training.EPS
                  else f"-{training.fmt_weight(-change, unit)}")
    first = history[0]["sets"][0]
    _stats([(training.amount(first["weight"], first["reps"], unit), f"first time, {_day(history[0]['performed_at']).strftime('%d %b')}", ""),
            (training.amount(best["weight"], best["reps"], unit), "best set", ""),
            (change_txt, "top set since then", "up" if change > training.EPS else "")])
    if len(history) < 2:
        st.caption("Log this exercise one more time and its curve appears here.")
        return
    rows = []
    for h in history:
        top_set = max(h["sets"], key=lambda s: (s["weight"], s["reps"]))
        rows.append({"Date": pd.to_datetime(h["performed_at"][:10]), "Value": round(training.to_unit(top_set["weight"], unit), 1)
                     if top_set["weight"] else top_set["reps"], "Set": training.amount(top_set["weight"], top_set["reps"], unit)})
    df = pd.DataFrame(rows)
    y_title = f"Top set ({unit})" if any(s["weight"] for s in all_sets) else "Most reps in a set"
    base = alt.Chart(df).encode(
        x=alt.X("Date:T", title=None, axis=alt.Axis(format="%d %b", grid=False, labelAngle=0, tickCount=5)),
        y=alt.Y("Value:Q", title=y_title, scale=alt.Scale(zero=False), axis=alt.Axis(gridOpacity=.15, tickCount=4)),
        tooltip=[alt.Tooltip("Date:T", format="%a %d %b"), alt.Tooltip("Set:N", title="Top set")])
    chart = (base.mark_line(color=color, strokeWidth=2, interpolate="monotone")
             + base.mark_point(color=color, filled=True, size=70, opacity=1)).properties(height=220)
    st.altair_chart(chart.configure_view(strokeWidth=0).configure(background="transparent"), width="stretch", theme="streamlit")
    st.caption("Your first time is your baseline. Each new best becomes the number to beat.")


# --- patterns, as plain sentences ---------------------------------------------------------------
def notes(sets, strength, unit):
    out = []
    today = date.today()
    recent_days = {_day(s["performed_at"]) for s in sets if (today - _day(s["performed_at"])).days < 28}
    if recent_days:
        out.append(f"Over the last 4 weeks you trained on {len(recent_days)} days, about {len(recent_days) / 4:.1f} a week.")
    if strength:
        gains = []
        for name in {s["exercise"] for s in strength}:
            hist = list(reversed(training.lift_history(strength, name)))
            if len(hist) >= 2:
                d = max(s["weight"] for s in hist[-1]["sets"]) - max(s["weight"] for s in hist[0]["sets"])
                gains.append((d, name))
        gains.sort(reverse=True)
        if gains and gains[0][0] > training.EPS:
            out.append(f"Biggest climb: {gains[0][1]}, up {training.fmt_weight(gains[0][0], unit)} on your top set since you started logging it.")
        month_prs = sum(1 for s in strength if s["is_pr"] and (today - _day(s["performed_at"])).days < 30)
        if month_prs:
            out.append(f"{month_prs} personal record{'s' if month_prs != 1 else ''} in the last 30 days.")
    all_days = sorted({_day(s["performed_at"]) for s in sets})
    gaps = [(b - a).days for a, b in zip(all_days, all_days[1:])]
    if gaps and max(gaps) >= 14:
        out.append(f"You once took {max(gaps)} days off and came back. Coming back is the hard part, and you did it.")
    if not out:
        return
    st.subheader("What we noticed", anchor=False)
    st.html("".join(f'<p class="pg-note">{html.escape(t)}</p>' for t in out))


# --- feeling stuck? (no new record in 4 weeks) ------------------------------------------------------------
def _amount(lift, top, unit):
    weight, reps = top
    return training.amount(weight, reps, unit, "hold" if lift in training.hold_names() else "reps")


def feeling_stuck(pages, sets, unit):
    """What's normal and what to check, with the person's own numbers. Never blames: a plateau is information."""
    s = targets.stuck(sets)
    if not s:
        return
    st.subheader("Feeling stuck?", anchor=False)
    st.html('<p class="pg-note">No new personal record in the last 4 weeks. That doesn\'t mean you\'re doing anything '
            "wrong. Strength usually climbs first, as your body learns the moves; muscle "
            "size changes slowly, and the studies BodySync uses saw clear changes after 9 to 12 weeks.</p>")
    week = f"{s['per_week']:.1f}".rstrip("0").rstrip(".")
    checks = [f"**Showing up.** You lifted on {s['days']} day{'s' if s['days'] != 1 else ''} in the last 4 weeks, "
              f"about {week} a week. " + ("That's a steady rhythm. " if s["per_week"] >= 2 else "")
              + research.do("frequency-2x")]
    if s["lift"]:
        a, b = _amount(s["lift"], s["first"], unit), _amount(s["lift"], s["last"], unit)
        checks.append(f"**Adding a little.** {s['lift']}, your most-done move: {a} at the start of these 4 weeks, {b} last time. "
                      + ("It is going up, even without a record. " if s["moved"]
                         else "One more rep at the same weight counts as progress too. ")
                      + research.do("progression-top-of-range"))
    checks.append("**Sleep.** " + research.do("sleep-strength"))
    checks.append("**Protein.** " + research.do("protein-1-6") + " Nutrition works out your number in grams.")
    st.markdown("Worth checking, one at a time:\n\n" + "\n".join(f"- {c}" for c in checks))
    if st.button("Work out my protein", icon=":material/restaurant:", key="pg_stuck_protein"):
        st.switch_page(pages["nutrition"])


# --- skills -----------------------------------------------------------------------------------
def skills_section(username, pages, sets):
    ladders = sk.all_ladders(session_data.custom_skills(username))
    state = {k: v for k, v in session_data.skills(username).items() if k in ladders}
    if not state:
        return
    st.subheader("Skills", anchor=False)
    for lid, gs in state.items():
        lad = ladders[lid]
        steps = lad["steps"]
        i = min(gs["step"], len(steps) - 1)
        names = {f"Skill: {s['name']}" for s in steps}
        practices = len({s["session_id"] for s in sets if s["exercise"] in names})
        st.markdown(f"**{lad['title']}**  ·  " + ("goal reached" if gs.get("done") else f"step {i + 1} of {len(steps)}: {steps[i]['name']}"))
        ui.stepper(len(steps), i, bool(gs.get("done")))
        st.caption(f"{practices} practice{'s' if practices != 1 else ''} logged" + (f"  ·  started {gs['started']}" if gs.get("started") else ""))
    st.page_link(pages["skills"], label="Go to Skills", icon=":material/arrow_forward:")


# --- history: repeat it, put it on your week, or remove it --------------------------------------------
def history(username, pages, sessions, unit):
    st.subheader("Workout history", anchor=False)
    undo = st.session_state.get("pg_undo")
    if undo:
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        c1.caption("Workout removed. Your totals were updated.")
        if c2.button("Undo", key="pg_undo_btn", width="stretch"):
            session_data.hide_session(username, undo, hide=False)
            st.session_state.pop("pg_undo", None)
            st.rerun()
    for n, sess in enumerate(sessions[:12]):
        prs = sum(1 for s in sess["sets"] if s["is_pr"])
        title = _title(username, sess)
        ex = find_exercise(sess["sets"][0]["exercise"].replace("Skill: ", ""))
        when = _day(sess["performed_at"]).strftime("%a %d %b")
        n_ex = len({s["exercise"] for s in sess["sets"]})
        opened, _ = ui.tap_row(f"hist{n}", (mini_url(ex) if ex else None) or "fitness_center", title,
                               f"{when}  ·  {n_ex} exercise{'s' if n_ex != 1 else ''}  ·  {len(sess['sets'])} sets"
                               + (f"  ·  {prs} PR" if prs else ""), icon=not ex)
        if opened:
            _session_dialog(username, pages, sess, unit, title)
    if len(sessions) > 12:
        st.caption(f"Showing your last 12 of {len(sessions)}. The export below has everything.")


def _names(sess):
    return list(dict.fromkeys(s["exercise"] for s in sess["sets"] if not s["exercise"].startswith(("Skill: ", "Walk: "))))


def _repeat(username, pages, sess, title):
    import today as today_page

    st.session_state.update(t_source=title, t_day="custom" if sess["day_type"] not in ("upper", "lower", "full") else sess["day_type"],
                            t_from_page="progress")
    today_page._begin(username, _names(sess))
    ui.to_workout(pages)


def _week_key(username, title, names):
    """The week planner's key for this workout: its playlist or curated workout, else a playlist made from it."""
    import plan
    import today as today_page

    if title in session_data.routines(username):
        return f"rt:{title}"
    w = next((x for x in today_page.curated() if x["title"] == title), None)
    if w:
        return f"cur:{w['id']}"
    for n in names:
        session_data.add_routine(username, title, [n], 3, 10, 0)
    return f"rt:{title}" if f"rt:{title}" in dict(plan.options(username)) else None


@st.dialog("Workout details")
def _session_dialog(username, pages, sess, unit, title):
    import plan

    st.markdown(f"**{title}**  ·  {_day(sess['performed_at']).strftime('%A %d %B %Y')}")
    for name in dict.fromkeys(s["exercise"] for s in sess["sets"]):
        rows = [s for s in sess["sets"] if s["exercise"] == name]
        st.markdown(f"**{name.replace('Skill: ', '').replace('Walk: ', '')}**")
        st.caption("  ·  ".join(
            (f"{r['reps']}" if sess["day_type"] == "skill" else training.amount(r["weight"], r["reps"], unit, training.kind_of(name, sess["day_type"])))
            + (" (PR)" if r["is_pr"] else "")
            for r in rows))
    names = _names(sess)
    st.divider()
    if names and st.button("Do this again now", type="primary", icon=":material/replay:", key="pg_rep", width="stretch"):
        _repeat(username, pages, sess, title)
    if names:
        st.markdown("**Add it to your week**")
        week = plan.get(username)
        day = st.segmented_control("Day", list(range(7)), format_func=lambda d: plan.DAYS[d][:3], key="pg_day",
                                   label_visibility="collapsed")
        if day is not None:
            current = week.get(str(day))
            if current:
                st.caption(f"{plan.DAYS[day]} already has {plan.label(username, current)}. Switch it for {title}?")
            if st.button(f"Yes, put it on {plan.DAYS[day]}" if current else f"Add to {plan.DAYS[day]}", key="pg_addweek",
                         width="stretch"):
                key = _week_key(username, title, names)
                if key:
                    plan.save(username, {**week, str(day): key})
                    st.toast(f"{title} is on {plan.DAYS[day]}", icon=":material/check_circle:")
                    st.rerun()
    st.divider()
    if st.button("Remove this workout", icon=":material/delete:", key="pg_rm", width="stretch", type="tertiary",
                 help="For test runs or mistakes. You can undo it right after."):
        session_data.hide_session(username, sess["session_id"])
        st.session_state["pg_undo"] = sess["session_id"]
        st.rerun()


def export(sets, unit):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "workout", "exercise", "set", f"weight_{unit}", "reps", "pr"])
    for s in sets:
        writer.writerow([s["performed_at"], s["day_type"], s["exercise"], s["set_no"],
                         round(training.to_unit(s["weight"], unit), 1), s["reps"], int(s["is_pr"])])
    st.write("")
    st.download_button("Export all my workouts (CSV)", buf.getvalue(), file_name="bodysync_workouts.csv", mime="text/csv",
                       icon=":material/download:", type="tertiary")
    st.caption("Your data is yours. The file opens in any spreadsheet app.")
