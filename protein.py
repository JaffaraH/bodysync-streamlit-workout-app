"""Protein today: a daily target from your body weight, a quick tally of what you ate or plan to eat,
and top-ups picked from foods you already have. No outside service needed.

Targets: 1.6 g per kg a day (research id protein-1-6), about 0.4 g per kg per meal over 4 meals
(protein-per-meal). Food values are rounded from USDA FoodData Central; labels vary, so people can edit them."""
from datetime import date
from html import escape

import streamlit as st

import research
import session_data

FDC_URL = "https://fdc.nal.usda.gov/"
G_PER_KG, MEALS = 1.6, 4

# name: (serving, grams of protein per serving). Rounded USDA FoodData Central values.
FOODS = {
    "Protein shake": ("1 scoop", 24),
    "Eggs": ("1 large egg", 6),
    "Milk": ("1 cup (240 ml)", 8),
    "Tuna, canned": ("100 g drained", 25),
    "Pasta, cooked": ("1 cup", 8),
    "Chicken breast": ("100 g cooked", 31),
    "Greek yogurt": ("170 g pot, plain", 17),
    "Cottage cheese": ("1/2 cup", 13),
    "Cheese": ("30 g slice", 7),
    "Lentils": ("1 cup cooked", 18),
    "Chickpeas": ("1 cup cooked", 14),
    "Black beans": ("1 cup cooked", 15),
    "Tofu, firm": ("100 g", 17),
    "Salmon": ("100 g cooked", 22),
    "Lean beef mince": ("100 g cooked", 26),
    "Peanut butter": ("2 tbsp", 7),
    "Bread": ("1 slice", 4),
    "Rice, cooked": ("1 cup", 4),
    "Oats": ("1/2 cup dry", 5),
}
CSS = """<style>
.bs-prot { border-radius: 16px; padding: 14px 16px; background: var(--bs-accent-soft); margin: 4px 0 12px; }
.bs-prot .n { font-size: 1.6rem; font-weight: 800; line-height: 1.1; }
.bs-prot .n small { font-size: .9rem; font-weight: 600; opacity: .75; }
.bs-prot .bar { height: 10px; border-radius: 99px; background: rgba(127,127,127,.22); margin: 10px 0 6px; overflow: hidden; }
.bs-prot .bar i { display: block; height: 100%; border-radius: 99px; background: var(--bs-accent-ink); }
.bs-prot p { margin: 0; font-size: .9rem; }
</style>"""


def target_g(weight_kg):
    return round(weight_kg * G_PER_KG), round(weight_kg * G_PER_KG / MEALS)


def top_ups(gap, have):
    """Close the gap with foods you already have: biggest protein per serving first, at most 3 suggestions,
    never more than 3 servings of one food, skipping foods much bigger than what's left. have: {food: grams per serving}. Returns [(food, servings, grams)]."""
    out = []
    for food, g in sorted(have.items(), key=lambda kv: -kv[1]):
        if gap <= 0 or len(out) == 3 or g <= 0:
            break
        n = min(3, round(gap / g))
        if n == 0:  # this food is too big for what's left: try a smaller one
            continue
        out.append((food, n, n * g))
        gap -= n * g
    return out


def _state(username):
    s = session_data.settings(username).get("protein") or {}
    if s.get("date") != date.today().isoformat():  # a new day: keep your foods and weight, clear the tally
        s = {**s, "date": date.today().isoformat(), "eaten": {}, "extras": []}
    return s


def my_meals(username):
    """Meals you saved: {"name", "foods": {food: servings}} from your tally, or {"name", "g"} from an AI idea."""
    return session_data.settings(username).get("my_meals") or []


def save_meal(username, meal):
    meals = [m for m in my_meals(username) if m["name"] != meal["name"]] + [meal]
    session_data.save_settings(username, my_meals=meals)


def _log_meal(username, meal):
    """Add a saved meal to today: its foods go into the servings boxes; an AI meal is one estimated line."""
    s = _state(username)
    if meal.get("foods"):
        for f, n in meal["foods"].items():
            st.session_state[f"pr_n_{f}"] = float(st.session_state.get(f"pr_n_{f}", (s.get("eaten") or {}).get(f, 0))) + n
        foods = list(dict.fromkeys(list(s.get("foods") or []) + list(meal["foods"])))
        st.session_state["pr_foods"] = foods
        _save(username, foods=foods)
    else:
        _save(username, extras=list(s.get("extras") or []) + [{"name": meal["name"], "g": int(meal.get("g") or 0)}])
    st.toast(f"Added {meal['name']} to today", icon=":material/check_circle:")


def _drop_extra(username, i):
    extras = list(_state(username).get("extras") or [])
    if 0 <= i < len(extras):
        extras.pop(i)
        _save(username, extras=extras)


def _save(username, **changes):
    session_data.save_settings(username, protein={**_state(username), **changes})


def _weight_kg(username, s):
    if s.get("weight_kg"):
        return float(s["weight_kg"])
    lb = (session_data.profile(username) or {}).get("weight")
    return round(float(lb) * 0.4536, 1) if lb else None


def section(username):
    st.subheader("Protein today", anchor=False)
    st.html(CSS)
    s = _state(username)
    unit = session_data.unit(username)
    kg = _weight_kg(username, s)
    shown = (round(kg / 0.4536) if unit == "lb" else kg) if kg else None
    w = st.number_input(f"Your body weight ({unit})", 30.0, 700.0, value=float(shown) if shown else None,
                        step=1.0, format="%.0f", placeholder="e.g. 150" if unit == "lb" else "e.g. 68", key="pr_w")
    if w is None:
        st.caption("Add your weight to get your daily protein target.")
        return
    kg_now = round(w * 0.4536, 1) if unit == "lb" else w
    if kg_now != s.get("weight_kg"):
        _save(username, weight_kg=kg_now)
    daily, per_meal = target_g(kg_now)

    custom = s.get("grams") or {}  # your own label values, e.g. a shake with 30 g a scoop
    grams = {f: int(custom.get(f, g)) for f, (_, g) in FOODS.items()}
    mine = [f for f in s.get("foods", ["Protein shake", "Eggs", "Milk"]) if f in FOODS]
    start = {} if "pr_foods" in st.session_state else {"default": mine}
    picked = st.pills("Foods you have", list(FOODS), selection_mode="multi", key="pr_foods", **start) or []
    if list(picked) != mine:
        _save(username, foods=list(picked))
    if not picked:
        st.caption("Pick the foods you have at home. You can change them any time.")
        return

    meals = my_meals(username)
    if meals:  # one tap: a meal you eat often goes straight into today
        st.caption("Your meals (tap to add to today):")
        with st.container(key="pr-meals"):
            cols = st.columns(min(3, len(meals)))
            for i, m in enumerate(meals):
                g = m.get("g") or sum(grams.get(f, 0) * n for f, n in (m.get("foods") or {}).items())
                cols[i % len(cols)].button(f"{m['name']} · {round(g)} g", key=f"pr_meal_{i}", width="stretch",
                                           on_click=_log_meal, args=(username, m), icon=":material/add:")
    st.caption("How many servings today, eaten or planned:")
    eaten = dict(s.get("eaten") or {})
    for f in picked:
        start = {} if f"pr_n_{f}" in st.session_state else {"value": float(eaten.get(f, 0))}  # a logged meal may have set it
        n = st.number_input(f"{f}: {FOODS[f][0]} = {grams[f]} g protein", min_value=0.0, max_value=20.0, step=0.5,
                            format="%g", key=f"pr_n_{f}", **start)
        eaten[f] = n
    if eaten != (s.get("eaten") or {}):
        _save(username, eaten=eaten)

    extras = list(s.get("extras") or [])
    for i, x in enumerate(extras):  # meals logged from an AI idea: one estimated line each
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f"**{escape(x['name'])}** · about {x['g']} g protein (estimate)")
        c2.button("", icon=":material/close:", key=f"pr_x_{i}", help="Remove", on_click=_drop_extra, args=(username, i))
    total = round(sum(grams[f] * n for f, n in eaten.items() if f in picked) + sum(x["g"] for x in extras))
    gap = daily - total
    pct = min(100, round(100 * total / daily)) if daily else 0
    status = (f"{gap} g to go. About {per_meal} g per meal over {MEALS} meals gets you there." if gap > 0
              else "You've reached today's target.")
    st.html(f'<div class="bs-prot"><div class="n">{total} g <small>of {daily} g protein today</small></div>'
            f'<div class="bar"><i style="width:{pct}%"></i></div><p>{escape(status)}</p></div>')

    if gap > 0:
        ups = top_ups(gap, {f: grams[f] for f in picked})
        if ups:
            st.markdown("**To close the gap with what you have**")
            for f, n, g in ups:
                amount = f"{n:g} × {FOODS[f][0]}"
                st.markdown(f"- {f}: {amount}, +{g} g")

    today_foods = {f: n for f, n in eaten.items() if f in picked and n}
    if today_foods:
        with st.popover("Save today's foods as a meal", icon=":material/bookmark_add:"):
            st.caption("Save what you ate as one meal (for example, Tuna pasta) and log it in one tap next time.")
            nm = st.text_input("Meal name", key="pr_meal_name", max_chars=40, placeholder="e.g. Tuna pasta")
            if st.button("Save meal", key="pr_meal_save", type="primary", disabled=not (nm or "").strip()):
                save_meal(username, {"name": nm.strip(), "foods": today_foods})
                st.toast(f"Saved {nm.strip()}", icon=":material/check_circle:")
                st.rerun()
    with st.popover("Edit protein per serving", icon=":material/edit:"):
        st.caption("Use the number on your label. Saved for next time.")
        new = {}
        for f in picked:
            new[f] = st.number_input(f"{f} ({FOODS[f][0]}), g", 0, 100, grams[f], key=f"pr_g_{f}")
        if st.button("Save", key="pr_g_save", type="primary"):
            _save(username, grams={**custom, **new})
            st.rerun()

    for rid in ("protein-1-6", "protein-per-meal"):
        why = research.why(rid)
        if why:
            st.caption("Why: " + why)
    st.caption(f"All numbers are estimates, rounded from [USDA FoodData Central]({FDC_URL}); your labels may differ. "
               "General guidance, not medical advice; if you have kidney disease, ask your doctor before eating "
               "more protein.")
    return {"daily": daily, "per_meal": per_meal, "total": total, "foods": list(picked)}
