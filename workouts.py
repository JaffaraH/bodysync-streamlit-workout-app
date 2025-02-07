# workouts.py
import streamlit as st
import os
import json
from PIL import Image
from google.cloud import bigquery
import config

# Define colors
PRIMARY_COLOR = "#B044E1"
SECONDARY_COLOR = "#F0F0F0"
ACCENT_COLOR = "#F54946"
TEXT_COLOR = "white"  # Text color is white

def initialize_bigquery_client():
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.google_application_credentials
        return bigquery.Client()
    except FileNotFoundError:
        print("Warning: Using less secure Application Default Credentials (ADC).")
        return bigquery.Client()

def workouts_page(username, _):
    menu = ["Explore Workout Database", "Saved Workouts", "Create Routines", "Saved Routines"]
    st.markdown('<h3 style="font-size: 24px;">Navigate Workout Pages: </h3>', unsafe_allow_html=True)
    choice = st.selectbox("", menu)
    st.write("-------")

    if choice == "Explore Workout Database":
        explore_workouts()
    elif choice == "Saved Workouts":
        display_saved_workouts()
    elif choice == "Create Routines":
        display_create_routines()
    elif choice == "Saved Routines":
        display_saved_routines()

def display_saved_routines():
    
    username = st.session_state.get("username", None)
    if username:
        st.markdown(
        f'<h1 style="text-align: center; color: {PRIMARY_COLOR}; font-family: "Roboto", sans-serif; font-size: 36px; padding-bottom: 0px; padding-top: 0px"> Saved Routines 📥</h1>\t\t',
        unsafe_allow_html=True
        )
        # Load saved playlists for the current user
        saved_playlists = get_saved_playlists(username)

        if saved_playlists:
            exercises_data = load_exercises()
            for playlist_name in saved_playlists:
                with st.expander(f"Saved Routines: {playlist_name}"):
                    playlist_workouts = get_playlist_workouts(username, playlist_name)
                    if playlist_workouts:
                        for workout in playlist_workouts:
                            workout_name = workout["workout_name"]
                            instructions = get_instructions(workout_name, exercises_data)
                            workout_images_dir = os.path.join(exercises_dir, workout_name.replace(" ", "_"))
                            workout_gif_path = os.path.join(workout_images_dir, f"{workout_name.replace(' ', '_')}.gif")

                            # Check if the directory exists
                            if not os.path.exists(workout_images_dir):
                                st.warning(f"Workout '{workout_name}' images directory not found.")
                                continue

                            # Check if the GIF exists, if not, create it
                            if not os.path.exists(workout_gif_path):
                                workout_images = [Image.open(os.path.join(workout_images_dir, img)) for img in os.listdir(workout_images_dir) if img.endswith(".jpg") or img.endswith(".png")]
                                create_gif(workout_images, workout_gif_path)
                            
                            # Display workout details
                            st.subheader(workout_name)
                            st.image(workout_gif_path, use_column_width=True)
                            st.markdown(instructions)
                            st.write(f"Duration: {workout['minutes']} minutes")
        else:
            st.info("This playlist is empty.")
    else:
        st.error("You need to be logged in to view Routine playlists.")

def get_playlist_workouts(username, workout_playlist):
    # Initialize BigQuery client
    client = bigquery.Client()

    # Construct the query to fetch workouts for the specified playlist
    query = f"""
    SELECT workout_name, reps, minutes, ss
    FROM `{project_id}.bodysyncusers.user_workout`
    WHERE username = @username AND workout_playlist = @workout_playlist
    """

    # Set query parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("username", "STRING", username),
            bigquery.ScalarQueryParameter("workout_playlist", "STRING", workout_playlist),
        ]
    )

    # Execute the query
    query_job = client.query(query, job_config=job_config)

    # Fetch results
    results = query_job.result()

    # Extract workout details from the results
    playlist_workouts = [
        {
            "workout_name": row["workout_name"],
            "reps": row["reps"],
            "minutes": row["minutes"],
            "ss": row["ss"]
        }
        for row in results
    ]

    return playlist_workouts

def get_saved_playlists(username):
    # Initialize BigQuery client
    client = bigquery.Client()

    # Construct the query to fetch saved playlists for the current user
    query = f"""
    SELECT DISTINCT workout_playlist
    FROM `{project_id}.bodysyncusers.user_workout`
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
    results = query_job.result()

    # Extract playlist names from the results
    saved_playlists = [row["workout_playlist"] for row in results]

    return saved_playlists

def display_create_routines():
    # Load exercise data
    exercises_data = load_exercises()

    # Section to create a custom workout playlist
    st.markdown(
        f'<h1 style="text-align: center; color: {PRIMARY_COLOR}; font-family: "Roboto", sans-serif; font-size: 36px; padding-bottom: 0px; padding-top: 0px"> Create Routines 📋</h1>\t\t',
        unsafe_allow_html=True
    )

    # Input fields for custom workout playlist
    workout_playlist = st.text_input("Routine Name", "")
    selected_exercises = st.multiselect("Select Exercises", [exercise["name"] for exercise in exercises_data])

    # Create a row with two columns for the reps input
    col1, col2 = st.columns(2)
    with col1:
        reps_sets = st.number_input("Sets", min_value=0, value=0)
    with col2:
        reps_reps = st.number_input("Reps", min_value=0, value=0)

    minutes = st.number_input("Minutes", min_value=0, value=0)

    # Save button for custom workout playlist
    if st.button("Save Playlist"):
        username = st.session_state.get("username", None)
        if username:
            # Loop over selected exercises to save each one in the playlist
            for workout_name in selected_exercises:
                if save_workout(username, workout_name, workout_playlist, reps_sets, reps_reps, minutes):
                    st.success(f"{workout_name} saved to {workout_playlist}!")
                    
                else:
                    st.error(f"Failed to save {workout_name} to {workout_playlist}.")
        else:
            st.error("You need to be logged in to create a playlist")

def save_workout(username, workout_name, workout_playlist, reps, minutes, ss):
    # Initialize BigQuery client
    client = bigquery.Client()

    # Construct the SQL query to insert the workout into the user_workout table
    query = f"""
    INSERT INTO `{project_id}.bodysyncusers.user_workout` (username, workout_name, workout_playlist, reps, minutes, ss)
    VALUES (@username, @workout_name, @workout_playlist, @reps, @minutes, @ss)
    """

    # Set query parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("username", "STRING", username),
            bigquery.ScalarQueryParameter("workout_name", "STRING", workout_name),
            bigquery.ScalarQueryParameter("workout_playlist", "STRING", workout_playlist),
            bigquery.ScalarQueryParameter("reps", "INTEGER", reps),
            bigquery.ScalarQueryParameter("minutes", "FLOAT", minutes),
            bigquery.ScalarQueryParameter("ss", "INTEGER", ss),
        ]
    )

    # Execute the query
    query_job = client.query(query, job_config=job_config)

    # Return True if the query was successful, otherwise return False
    try:
        query_job.result()  # Wait for the query to finish
        return True
    except Exception as e:
        print(f"Error saving workout: {e}")
        return False


def display_saved_workouts():
    st.markdown(
        f'<h1 style="text-align: center; color: {PRIMARY_COLOR}; font-family: "Roboto", sans-serif; font-size: 36px; padding-bottom: 0px; padding-top: 0px"> Saved Workouts 📥</h1>\t\t',
        unsafe_allow_html=True
    )

    # Load exercise data
    exercises_data = load_exercises()

    # Get the username from the session state
    username = st.session_state.get("username", None)

    if username:
        # Initialize BigQuery client
        client = bigquery.Client()

        # Construct the query to fetch saved workouts for the current user
        query = f"""
        SELECT workout_name
        FROM `{project_id}.bodysyncusers.saved_workouts`
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
        saved_workouts = [row["workout_name"] for row in query_job.result()]

        if saved_workouts:
            # Display existing saved workouts
            for workout_name in saved_workouts:
                # Check if the workout is present in the exercises data
                workout_details = next((exercise for exercise in exercises_data if exercise["name"] == workout_name), None)

                if workout_details:
                    workout_instructions = get_instructions(workout_name, exercises_data)
                    workout_id = workout_details["id"]
                    workout_images_dir = os.path.join(exercises_dir, workout_id)
                    workout_gif_path = os.path.join(workout_images_dir, f"{workout_id}.gif")

                    # Check if the directory exists
                    if not os.path.exists(workout_images_dir):
                        st.warning(f"Workout '{workout_name}' images directory not found.")
                        continue

                    # Check if the GIF exists, if not, create it
                    if not os.path.exists(workout_gif_path):
                        workout_images = [Image.open(os.path.join(workout_images_dir, img)) for img in os.listdir(workout_images_dir) if img.endswith(".jpg") or img.endswith(".png")]
                        create_gif(workout_images, workout_gif_path)

                    # Display workout details
                    st.subheader(workout_name)
                    st.image(workout_gif_path, use_column_width=True)
                    st.markdown("\n".join(workout_instructions))

                else:
                    st.warning(f"Workout '{workout_name}' details not found.")

        else:
            st.info("You have no saved workouts.")
    else:
        st.error("You need to be logged in to view saved workouts.")

def explore_workouts():
    # Load exercise data
    exercises_data = load_exercises()

    if exercises_data:

        st.markdown(
        f'<h1 style="text-align: center; color: {PRIMARY_COLOR}; font-family: "Roboto", sans-serif; font-size: 36px; padding-bottom: 0px; padding-top: 0px"> Explore Workout Database 💪</h1>\t\t',
        unsafe_allow_html=True
        )


        # Search Workouts
        search_query = st.text_input("Search Workouts", "")

        # Add tabs under text
        #st.write("&nbsp;", unsafe_allow_html=True)

        # Toggleable sections for filter options
        with st.expander("Filter Workouts"):
            categories = sorted(set(exercise["category"] for exercise in exercises_data))
            forces = sorted(set(exercise["force"] for exercise in exercises_data if exercise["force"]))
            levels = sorted(set(exercise["level"] for exercise in exercises_data))
            equipment = sorted(set(exercise["equipment"] for exercise in exercises_data if exercise["equipment"]))

            category_filter = st.multiselect("Category", categories)
            force_filter = st.multiselect("Force", forces)
            level_filter = st.multiselect("Level", levels)
            equipment_filter = st.multiselect("Equipment", equipment)

        filtered_exercises = exercises_data
        if category_filter:
            filtered_exercises = [exercise for exercise in filtered_exercises if exercise["category"] in category_filter]
        if force_filter:
            filtered_exercises = [exercise for exercise in filtered_exercises if exercise["force"] in force_filter]
        if level_filter:
            filtered_exercises = [exercise for exercise in filtered_exercises if exercise["level"] in level_filter]
        if equipment_filter:
            filtered_exercises = [exercise for exercise in filtered_exercises if exercise["equipment"] in equipment_filter]
        if search_query:
            filtered_exercises = [exercise for exercise in filtered_exercises if search_query.lower() in exercise["name"].lower()]

        # Display filtered exercises
        for exercise in filtered_exercises:
            workout_name = exercise["name"]
            workout_instructions = exercise["instructions"]
            workout_images = [Image.open(os.path.join(exercises_dir, img_path)) for img_path in exercise["images"]]
            workout_id = exercise["id"]
            workout_gif_path = f"{config.exercises_dir}/{workout_id}/{workout_id}.gif"
            # Create GIF from images if it doesn't exist
            if not os.path.exists(workout_gif_path):
                create_gif(workout_images, workout_gif_path)

            # Display workout details
            st.subheader(workout_name)
            st.image(workout_gif_path, use_column_width=True)
            st.markdown("\n".join(workout_instructions))

            # Check if the workout is already saved
            username = st.session_state.get("username", None)
            is_saved = False
            if username:
                is_saved = check_workout_saved(username, workout_name)

            # Save button
            if os.path.exists(workout_gif_path):  # Check if the image exists
                if is_saved:
                    st.button(f"Already Saved {workout_name}", disabled=True)
                else:
                    if st.button(f"Save {workout_name}"):
                        if username:
                            # Call the new function to save the workout
                            if save_one_workout(username, workout_name):
                                st.success(f"{workout_name} saved!")
                            else:
                                st.error(f"Failed to save {workout_name}.")
                        else:
                            st.error("You need to be logged in to save workouts.")
            else:
                st.warning("Image not available. Unable to save workout.")


def load_exercises():
    # Load exercise data from exercises.json
    with open(exercises_json_path, "r") as f:
        exercises_data = json.load(f)
    return exercises_data

def get_instructions(workout_name, exercises_data):
    for exercise in exercises_data:
        if exercise["name"] == workout_name:
            return exercise.get("instructions", "Instructions not found")


def create_gif(images, output_path):
    # Create GIF from a list of images
    images[0].save(output_path, save_all=True, append_images=images[1:], duration=500, loop=0)

def check_workout_saved(username, workout_name):
    # Initialize BigQuery client
    client = bigquery.Client()

    # Construct the query
    query = f"""
    SELECT workout_name
    FROM `{project_id}.bodysyncusers.saved_workouts`
    WHERE username = @username AND workout_name = @workout_name
    """

    # Set query parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("username", "STRING", username),
            bigquery.ScalarQueryParameter("workout_name", "STRING", workout_name),
        ]
    )

    # Execute the query
    query_job = client.query(query, job_config=job_config)

    # Fetch results
    result = query_job.result()

    # Check if workout_name exists in the result set
    for row in result:
        return True

    return False

def save_one_workout(username, workout_name):
    # Check if the workout is already saved for the user
    if check_workout_saved(username, workout_name):
        st.warning(f"{workout_name} is already saved!")
        return False

    # If the workout is not saved, proceed to save it
    try:
        # Initialize BigQuery client
        client = bigquery.Client()

        # Construct the SQL query to insert the workout into the user_workout table
        query = f"""
        INSERT INTO `{project_id}.bodysyncusers.saved_workouts` (username, workout_name)
        VALUES (@username, @workout_name)
        """

        # Set query parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("username", "STRING", username),
                bigquery.ScalarQueryParameter("workout_name", "STRING", workout_name),
            ]
        )

        # Execute the query
        query_job = client.query(query, job_config=job_config)

        # Return True if the query was successful
        return True

    except Exception as e:
        st.error(f"Error saving workout: {e}")
        return False

# Path to the exercises directory & json
exercises_dir = config.exercises_dir
exercises_json_path = config.exercises_json_path
project_id = config.PROJECT_ID


