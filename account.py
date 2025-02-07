import streamlit as st
import os
from google.cloud import bigquery
import config

project_id = config.PROJECT_ID

def initialize_bigquery_client():
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.google_application_credentials
        return bigquery.Client()
    except FileNotFoundError:
        print("Warning: Using less secure Application Default Credentials (ADC).")
        return bigquery.Client()
def nutrition_page(username, _):
    st.markdown("<h2 style='color: #B044E1;'>Explore Recipes 🥗</h2>", unsafe_allow_html=True)

    # Get user profile data
    user_profile_data = get_user_profile_data(username)
    
    # Check if user_profile_data is None
    if user_profile_data is None:
        st.error("Failed to retrieve user profile information.")
        return
    
    age, weight, height, fitness_level, health_condition = user_profile_data

    explore_recipes(username)

def save_profile_info(username, age, weight, height, fitness_level, health_condition):
    try:
        bq_client = initialize_bigquery_client()
        query = f"""
        INSERT INTO `{project_id}.bodysyncusers.saved_profile` (username, age, weight, height, fitness_level, health_condition)
        VALUES ('{username}', {age}, {weight}, {height}, '{fitness_level}', '{health_condition}')
        """
        query_job = bq_client.query(query)
        query_job.result()
        return True  # Profile information saved successfully
    except Exception as e:
        st.error(f"Error saving profile information: {e}")
        return False  # Failed to save profile information

def get_profile_info(username):
    try:
        bq_client = initialize_bigquery_client()
        query = f"""
        SELECT age, weight, height, fitness_level, health_condition
        FROM `{project_id}.bodysyncusers.saved_profile`
        WHERE username = @username
        """
        query_params = [bigquery.ScalarQueryParameter("username", "STRING", username)]
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        query_job = bq_client.query(query, job_config=job_config)
        results = list(query_job.result())
        if results:
            profile_info = {
                "age": results[0]['age'],
                "weight": results[0]['weight'],
                "height": results[0]['height'],
                "fitness_level": results[0]['fitness_level'],
                "health_condition": results[0]['health_condition']
            }
            return profile_info
    except Exception as e:
        st.error(f"Error retrieving profile information: {e}")
        return None

def profile_page(username, _):
    st.markdown(
        f"""<h3 style="text-align: center; font-family: 'Roboto', sans-serif; font-size: 36px; padding-bottom: 0px; padding-top: 0px"> 👤 {username} </h3>""",
        unsafe_allow_html=True
    )
    st.write("-------")
    
    # Get profile info based on the username
    profile_info = get_profile_info(username) if username else None

    # Initialize fields with existing information or default values
    if profile_info:
        age = int(profile_info.get("age", 0))
        weight = float(profile_info.get("weight", 0))
        height = float(profile_info.get("height", 0))
        fitness_level = profile_info.get("fitness_level", "")
        health_condition = profile_info.get("health_condition", "")
    else:
        age, weight, height, fitness_level, health_condition = 0, 0.0, 0.0, "", ""

    # Add UI components to capture user's profile details
    age = st.number_input("Age", min_value=0, max_value=150, value=age)
    weight = st.number_input("Weight (lbs)", min_value=0.0, max_value=500.0, value=weight)
    height = st.number_input("Height (ft)", min_value=0.0, max_value=300.0, value=height)
    
    # Modified input for fitness level
    fitness_level = st.selectbox("Fitness Level", ["Beginner", "Intermediate", "Advanced"], help="Select your current fitness level.")
    
    health_conditions = st.text_area("Health Condition (leave empty if none)", value=health_condition)

    # Save profile info when user submits
    if st.button("Save Profile"):
        if save_profile_info(username, age, weight, height, fitness_level, health_condition):
            st.success("Profile information saved successfully!")
            st.balloons()
        else:
            st.error("Failed to save profile information. Please try again.")