import requests
import streamlit as st

import ai
import protein
import config
import session_data
import ui

CUISINES = [
    "Mexican", "Chinese", "Japanese", "Indian", "Thai", "Middle Eastern", "Brazilian", "Greek", "American",
    "Italian", "Vietnamese", "Korean", "Ethiopian", "Nigerian", "Somali", "Jamaican",
]
# Our friendly restriction -> Edamam "health" labels
HEALTH_LABELS = {
    "Vegan": ["vegan"], "Vegetarian": ["vegetarian"], "Pescetarian": ["pescatarian"],
    "Halal": ["pork-free", "alcohol-free"], "Kosher": ["kosher"], "Gluten-free": ["gluten-free"],
    "Dairy-free": ["dairy-free"], "Lactose-free": ["dairy-free"], "Nut-free": ["tree-nut-free", "peanut-free"],
    "Soy-free": ["soy-free"], "Shellfish-free": ["shellfish-free"], "Seafood-free": ["fish-free", "shellfish-free"],
    "Sugar-free": ["sugar-conscious"], "Low sugar": ["low-sugar"],
}
EDAMAM_READY = bool(config.EDAMAM_APP_ID and config.EDAMAM_APP_KEY)


def nutrition_page(username, pages):
    ui.back_to_you(pages)
    st.title("Nutrition")
    info = protein.section(username)
    st.divider()
    meal_from_pantry(username, info)
    if not EDAMAM_READY:  # recipe search needs Edamam keys; without them the AI tools below still work
        st.divider()
        st.subheader("Weekly meal plan", anchor=False)
        ai_week_plan(username)
        return
    st.divider()
    st.subheader("Find recipes", anchor=False)
    with st.form("nutrition_form"):
        food = st.text_input("What are you in the mood for?", placeholder="chicken, lentils, salmon...")
        c1, c2, c3 = st.columns(3)
        min_protein = c1.number_input("Min. protein (g)", 0, 200, value=None, placeholder="e.g. 30")
        cal_min = c2.number_input("Min. calories", 0, 3000, value=None, placeholder="e.g. 300", step=50)
        cal_max = c3.number_input("Max. calories", 0, 3000, value=None, placeholder="e.g. 600", step=50)
        cuisines = st.multiselect("Cuisines (used for the AI meal plan)", CUISINES)
        restrictions = st.multiselect("Dietary restrictions", list(HEALTH_LABELS))
        b1, b2 = st.columns(2)
        find = b1.form_submit_button("Find recipes", disabled=not EDAMAM_READY, width="stretch")
        plan = b2.form_submit_button("AI weekly meal plan", type="primary", disabled=not ai.is_configured(), width="stretch")

    calories = f"{cal_min or 0}-{cal_max}" if cal_max else (f"{cal_min}+" if cal_min else None)

    if find:
        if not food.strip():
            st.error("Tell us what you're after (e.g. chicken) and search again.")
        else:
            with st.spinner("Searching recipes..."):
                st.session_state["recipes"] = search_recipes(username, food, min_protein, calories, restrictions)

    if plan:
        prompt = f"""Create a 7-day meal plan (breakfast, lunch, dinner each day).

Preferences:
- Dish idea: {food or 'any'}
- Protein target: {min_protein or 'not specified'} g per meal
- Calories per meal: {calories or 'not specified'}
- Cuisines: {', '.join(cuisines) or 'any'}
- Dietary restrictions: {', '.join(restrictions) or 'none'}
About the user: {session_data.profile_summary(username)}

For each meal give the dish name, estimated calories and protein, ingredients and 2-3 line instructions.
Respect every dietary restriction strictly and flag common allergens."""
        text = ui.stream_into_chat(ai.stream(prompt, username=username), "Planning your week...")
        if text is None:
            st.caption("Your choices are kept. Press the button again to retry.")
        else:
            st.session_state["meal_plan"] = text
    elif st.session_state.get("meal_plan"):
        with st.chat_message("assistant", avatar=":material/smart_toy:"):
            st.markdown(ui.no_media(st.session_state["meal_plan"]))
    if st.session_state.get("meal_plan"):
        st.download_button("Download meal plan", st.session_state["meal_plan"], file_name="bodysync_meal_plan.md")

    recipes = st.session_state.get("recipes")
    if recipes is not None:
        show_recipes(recipes)


def search_recipes(username, food, min_protein, calories, restrictions):
    params = {
        "q": food, "app_id": config.EDAMAM_APP_ID, "app_key": config.EDAMAM_APP_KEY, "type": "public",
    }
    if protein:
        params["nutrients[PROCNT]"] = f"{protein}+"
    if calories:
        params["calories"] = calories
    labels = sorted({label for r in restrictions for label in HEALTH_LABELS[r]})
    if labels:
        params["health"] = labels
    try:
        r = requests.get(
            "https://api.edamam.com/api/recipes/v2", params=params,
            headers={"Edamam-Account-User": username}, timeout=20,
        )
        r.raise_for_status()
        return r.json().get("hits", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Recipe search failed ({type(e).__name__}). Check your Edamam keys and connection, then try again.")
        return None


def show_recipes(hits):
    if hits == []:
        ui.empty_state("No recipes found", "Try a simpler search or loosen the protein/calorie limits.", icon="restaurant")
        return
    if not hits:
        return
    st.subheader(f"{len(hits)} recipes")
    cols = st.columns(2)
    for i, hit in enumerate(hits):
        r = hit["recipe"]
        servings = r.get("yield") or 1
        kcal = round(r.get("calories", 0) / servings)
        protein = round(r.get("totalNutrients", {}).get("PROCNT", {}).get("quantity", 0) / servings)
        with cols[i % 2], st.container(border=True):
            if r.get("image"):
                st.image(r["image"], width="stretch")
            st.markdown(f"**{r['label']}**")
            time = f" · {int(r['totalTime'])} min" if r.get("totalTime") else ""
            st.caption(f"~{kcal} kcal · {protein} g protein per serving{time}")
            with st.expander("Ingredients"):
                for ing in r.get("ingredients", []):
                    st.write(f"- {ing['text']}")
            st.link_button("View recipe", r["url"], width="stretch")


def meal_from_pantry(username, info):
    """One meal from what's in your kitchen, aimed at your protein per meal (AI, optional). Log it for today, or
    save it to your meals for one-tap logging later. Numbers are AI estimates and say so."""
    st.subheader("Meal idea from what I have", anchor=False)
    ui.ai_key_notice(username)
    foods = (info or {}).get("foods") or []
    extra = st.text_input("Anything else in your kitchen?", placeholder="e.g. pasta, tomatoes, spinach, onion",
                          key="nu_pantry")
    meal = st.segmented_control("Which meal", ["Breakfast", "Lunch", "Dinner", "Snack"], default="Dinner",
                                key="nu_meal")
    go = st.button("Make me a meal", type="primary", icon=":material/restaurant:", key="nu_make", width="stretch",
                   disabled=not ai.is_configured() or not (foods or extra.strip()))
    if not ai.is_configured():
        st.caption(":material/key: Turn on AI above to use this.")
    if go:
        need = (info or {}).get("per_meal")
        have = ", ".join(foods + ([extra.strip()] if extra.strip() else []))
        prompt = f"""Suggest ONE simple {(meal or 'dinner').lower()} using mostly these ingredients: {have}.
Protein goal for this meal: {f'about {need} g' if need else 'as much as is reasonable'}.
About the person: {session_data.profile_summary(username)}
Only use common staples beyond the list (oil, salt, spices). Flag common allergens.
Reply as JSON only: {{"name": "dish name", "ingredients": ["amount + ingredient"], "steps": ["3 to 5 short steps"],
"protein_g": 30, "swap": "one easy swap or add-on from the list that adds protein", "allergens": "..."}}"""
        with st.spinner("Cooking something up..."):
            try:
                st.session_state["nu_meal_idea"] = ai.ask_json(prompt, username=username)
            except Exception as e:
                st.error(ai.friendly_error(e))
                return
    idea = st.session_state.get("nu_meal_idea")
    if not idea or not idea.get("name"):
        return
    with st.container(border=True):
        g = int(idea.get("protein_g") or 0)
        st.markdown(f"#### {ui.no_media(idea['name'])}")
        st.caption(f"About {g} g protein per serving (an AI estimate; check your labels)")
        st.markdown(ui.no_media("\n".join(f"- {x}" for x in idea.get("ingredients") or [])))
        st.markdown(ui.no_media("\n".join(f"{i}. {x}" for i, x in enumerate(idea.get("steps") or [], 1))))
        if idea.get("swap"):
            st.caption(ui.no_media(f"More protein: {idea['swap']}"))
        if idea.get("allergens"):
            st.caption(ui.no_media(f"Allergens: {idea['allergens']}"))
        with st.container(key="keep-nu-meal"):
            a, b = st.columns(2)
            if a.button("Log it for today", icon=":material/add:", key="nu_log", width="stretch"):
                protein._log_meal(username, {"name": idea["name"], "g": g})
                st.rerun()
            if b.button("Save to my meals", icon=":material/bookmark_add:", key="nu_keep", width="stretch"):
                protein.save_meal(username, {"name": idea["name"], "g": g})
                st.toast(f"Saved {idea['name']}. It's in Your meals above.", icon=":material/check_circle:")
                st.rerun()


def ai_week_plan(username):
    with st.form("nu_week"):
        cuisines = st.multiselect("Cuisines you like", CUISINES)
        restrictions = st.multiselect("Dietary restrictions", list(HEALTH_LABELS))
        go = st.form_submit_button("Plan my week", type="primary", disabled=not ai.is_configured())
    if go:
        daily = (protein._state(username).get("weight_kg") or 0) * protein.G_PER_KG
        prompt = f"""Create a 7-day meal plan (breakfast, lunch, dinner each day).
Daily protein target: {f'about {round(daily)} g' if daily else 'not specified'}.
Cuisines: {', '.join(cuisines) or 'any'}. Dietary restrictions: {', '.join(restrictions) or 'none'}.
About the user: {session_data.profile_summary(username)}
For each meal: dish name, estimated calories and protein, short ingredient list. Keep it cheap and simple,
reuse ingredients across days, and end with a grocery list. Respect every restriction strictly; flag allergens."""
        text = ui.stream_into_chat(ai.stream(prompt, username=username), "Planning your week...")
        if text is not None:
            st.session_state["meal_plan"] = text
    elif st.session_state.get("meal_plan"):
        with st.chat_message("assistant", avatar=":material/smart_toy:"):
            st.markdown(ui.no_media(st.session_state["meal_plan"]))
    if st.session_state.get("meal_plan"):
        st.download_button("Download meal plan", st.session_state["meal_plan"], file_name="bodysync_meal_plan.md")
