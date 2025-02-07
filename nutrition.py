import streamlit as st
import os
from google.cloud import bigquery
import config
import requests
import google.generativeai as genai

project_id = config.PROJECT_ID

def initialize_bigquery_client():
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.google_application_credentials
        return bigquery.Client()
    except FileNotFoundError:
        print("Warning: Using less secure Application Default Credentials (ADC).")
        return bigquery.Client()

def nutrition_page(username, _):
    age, weight, height, fitness_level, health_condition = get_user_profile_data(username)

    st.markdown("<h2 style='color: #B044E1;'>Explore Recipes 🥗</h2>", unsafe_allow_html=True)

    explore_recipes(username)

def explore_recipes(username):
    # User inputs
    food_choice = st.text_input("Enter the food you want a recipe for:")
    protein_amount = st.number_input("Enter how much protein you need (grams):")
    calorie_range = st.text_input("Enter the range of calories you want (e.g., 300-400):")
    cuisine_choice = st.multiselect("Select your preferred cuisine:", 
    ['Mexican', 'Chinese', 'Japanese', 'Indian', 'Thai', 'Middle Eastern', 'Brazilian', 'Greek', 'American',
     'Italian', 'Vietnamese', 'Korean', 'Ethiopian', 'Nigerian', 'Somali', 'Jamaican'])

    dietary_restrictions = st.multiselect("Select your dietary restrictions:", 
    ['Vegan','Vegetarian','Pescetarian', 'Halal', 'Kosher', 'Gluten-free', 'Dairy-free','Nut-free','Soy-free',
    'Shellfish-free', 'Seafood-free', 'Sugar-free', 'Low sugar', 'Lactose-free'])

    # Button to search for recipes
    if st.button("Search"):
        # Call API to get high-protein recipes
        recipes = get_high_protein_recipes(food_choice, protein_amount, calorie_range)

        # Display recipes
        if recipes:
            for idx, recipe_data in enumerate(recipes, 1):
                recipe = recipe_data.get('recipe')
                st.subheader(f"Recipe {idx}: {recipe['label']}")

                # Display image
                if recipe['image']:
                    st.image(recipe['image'])
                st.write("Link:", recipe['url'])

                # Display recipe details in an expander
                with st.expander("Recipe Details"):
                    st.write("Ingredients:")
                    for ingredient in recipe['ingredients']:
                        st.write(f"- {ingredient['text']}")
    if st.button("Generate Meal Plan with AI"):
        user_profile_data = get_user_profile_data(username)
        if user_profile_data:
            age, weight, height, fitness_level, health_condition = user_profile_data
        # Use the user's query data to generate the AI response
        ai_prompt = f"""
            Weekly Meal Plan

            Based on the user's preferences and nutritional goals, create a weekly meal plan incorporating a variety of dishes similar to the cuisine and dish they have queried.

            User Preferences:
            - Food Dish Query: {food_choice}
            - Protein Amount: {protein_amount} grams
            - Calorie Range for meals: {calorie_range}
            - Cuisine Choices: {', '.join(cuisine_choice)}
            - Dietary Restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}

            User Profile:
            - Age: {age} years
            - Weight: {weight} lbs
            - Height: {height} ft
            - Fitness Level: {fitness_level}
            - Health Conditions: {health_condition if health_condition else 'None'}

            Meal Plan Details:
            - The meal plan will provide a comprehensive outline of each meal for each day of the week, tailored to the user's preferences and nutritional needs.
            - Each meal will be designed to fit within the specified calorie range and meet the desired protein intake.
            - Recipes will be selected based on the user's queried dish and preferred cuisines, ensuring variety and enjoyment.
            - Nutritional information, including estimated calories, protein content, and key nutrients, will be provided for each recipe.
            - Ingredient lists, cooking tools, and detailed instructions will be included to guide users through meal preparation.
            - Recommendations for portion sizes, macronutrient distribution, and suggested meal timings will support the user's overall health and fitness goals.
            - Where applicable, dietary modifications or alternatives will be provided to accommodate specific dietary preferences or restrictions.

            **Weekly Plan:**
            - **Day 1:**
            - **Breakfast:**
                - Recipe: [Breakfast Recipe Name]
                - Calories: [Calories]
                - Protein: [Protein]
                - Ingredients: [Ingredients]
    
            - **Lunch:**
                - Recipe: [Lunch Recipe Name]
                - Calories: [Calories]
                - Protein: [Protein]
                - Ingredients: [Ingredients]

            - **Dinner:**
                - Recipe: [Dinner Recipe Name]
                - Calories: [Calories]
                - Protein: [Protein]
                - Ingredients: [Ingredients]

            - **Day 2:**
            - **Breakfast:** [Same structure as Day 1]
            - **Lunch:** [Same structure as Day 1]
            - **Dinner:** [Same structure as Day 1]
            - **Day 3:**
            - **Breakfast:** [Same structure as Day 1]
            - **Lunch:** [Same structure as Day 1]
            - **Dinner:** [Same structure as Day 1]
            - **Day 4:**
            - **Breakfast:** [Same structure as Day 1]
            - **Lunch:** [Same structure as Day 1]
            - **Dinner:** [Same structure as Day 1]
            - **Day 5:**
            - **Breakfast:** [Same structure as Day 1]
            - **Lunch:** [Same structure as Day 1]
            - **Dinner:** [Same structure as Day 1]
            - **Day 6:**
            - **Breakfast:** [Same structure as Day 1]
            - **Lunch:** [Same structure as Day 1]
            - **Dinner:** [Same structure as Day 1]
            - **Day 7:**
            - **Breakfast:** [Same structure as Day 1]
            - **Lunch:** [Same structure as Day 1]
            - **Dinner:** [Same structure as Day 1]
            """
        # Configure the Gen AI API with your API key
        genai.configure(api_key=config.API_KEY)
        # Create a GenerativeModel instance
        model = genai.GenerativeModel('gemini-pro')

        # Generate content based on the user's input
        ai_response = model.generate_content(ai_prompt)
        # Display the AI-generated response
        st.success("AI Response generated")
        st.write(ai_response.text)

        # Download button for the AI-generated workout plan
        st.download_button(label="Download Meal Plan", data=ai_response.text, file_name="AI_generated_meal_plan.txt", mime="text/plain")


def get_high_protein_recipes(food_choice, protein_amount, calorie_range):
    try:
        app_id = config.app_id
        api_key = config.api_key_n

        params = {
            "q": food_choice,
            "app_id": app_id,
            "app_key": api_key,
            "type": "public",
            "nutrients[PROCNT]": f"{protein_amount}+",
            "calories": calorie_range,
        }

        response = requests.get("https://api.edamam.com/api/recipes/v2", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('hits', [])
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred: {e}")
        return []

def get_user_profile_data(username):
    # Initialize BigQuery client
    client = bigquery.Client()

    # Construct the query
    query = f"""
    SELECT age, weight, height, fitness_level, health_condition
    FROM `{project_id}.bodysyncusers.saved_profile`
    WHERE username = @username
    """

    # Set query parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("username", "STRING", username),
        ]
    )

    # Execute the query
    query_job = client.query(query, job_config=job_config)

    # Fetch results
    result = query_job.result()

    # Process the results
    for row in result:
        return row["age"], row["weight"], row["height"], row["fitness_level"], row["health_condition"]
