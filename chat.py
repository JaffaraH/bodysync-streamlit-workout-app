import streamlit as st
import hashlib
import time  # Import time module for delay
from google.cloud import bigquery
import os
import config
from PIL import Image
import json
from vertexai.preview.vision_models import ImageGenerationModel
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import requests
import google.generativeai as genai

project_id = config.PROJECT_ID

def chat_page(username, _):
    st.markdown("<h2 style='color: #B044E1;'>Discover Workout Routines with AI 💬</h2>", unsafe_allow_html=True)
    workout_preference = st.text_input("What's your fitness goal?", help="E.g., 'lose weight', 'gain muscle'")

    if workout_preference:
        # Fetch username from session state
        username = st.session_state.get("username", None)
        if username:
            # Fetch user profile data from the database
            user_profile_data = get_user_profile_data(username)
            if user_profile_data:
                age, weight, height, fitness_level, health_condition = user_profile_data

                # Use the fetched data to generate the AI response
                ai_response_text = f"""
                Based on the user's profile, a comprehensive 3-day workout plan aligning with the '{workout_preference}' workout preference is recommended. 
                The workout plan is designed to meet the user's fitness goals, considering:

                User Profile:
                - Age: {age} years
                - Weight: {weight} kg
                - Height: {height} cm
                - Fitness Level: {fitness_level}
                - Health Conditions: {health_condition}

                The workout plan will detail exercises for each day, focusing on {workout_preference}. Recommendations will include exercise type, duration, intensity, and suggested rest periods to ensure a balanced approach to achieving fitness goals. Where applicable, modifications for health conditions or fitness level will be provided to ensure safety and effectiveness.
                """

                # Configure the Gen AI API with your API key
                genai.configure(api_key=config.API_KEY)
                # Create a GenerativeModel instance
                model = genai.GenerativeModel('gemini-pro')

                # Generate content based on the user's input
                ai_response = model.generate_content(ai_response_text)
                # Display the AI-generated response
                st.success("AI Response generated")
                st.write(ai_response.text)

                # Download button for the AI-generated workout plan
                st.download_button(label="Download Workout Plan", data=ai_response.text, file_name="AI_generated_workout_plan.txt", mime="text/plain")

                if st.button("Generate the estimate time for the workout"):
                    ai_response2 = model.generate_content("Generate the estimate time for the workout " + ai_response.text)
                    st.success("AI Estimated time:")
                    st.write(ai_response2.text)

            else:
                st.error("Failed to retrieve user profile data.")
        else:
            st.error("You need to be logged in to generate a workout plan.")
    else:
        st.write("Please enter your workout preferences to generate and download a workout plan.")
        
    st.markdown("<h2 style='color: #B044E1;'>Gym Machine Usage Guide</h2>", unsafe_allow_html=True)
    # File Upload Section
    file = st.file_uploader("Upload an Image of the Gym Machine", help="Upload a clear image of the gym machine you need instructions for.")
    if file is not None:
        img = Image.open(file)
        st.image(img)
        genai.configure(api_key=config.API_KEY)
        model = genai.GenerativeModel('gemini-pro-vision')
        response2 = model.generate_content([ 'Provide clear and concise instructions on how to use a specific gym machine in a well-organized bullet-point format. Include the following details: the name of the workout associated with the machine, the targeted muscle groups, step-by-step instructions on using the machine effectively.', img])
        
        response2.resolve()
        st.success("AI Response generated")
        st.write(response2.text)

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
