#streamlit run /home/huda_jaffara/final-project-superbees/Part\ 6\ Deploy\ App/part_6_deploy/homepage.py --server.enableCORS=false
# #3498DB ##F0F0F0 #F54946
import streamlit as st
import hashlib
import time
from google.cloud import bigquery
import json
import config
from streamlit_option_menu import option_menu
from home import home_page
from account import profile_page
from chat import chat_page
from nutrition import nutrition_page
from workouts import workouts_page

DEFAULT_PAGE = "1_🔐_Login.py"
project_id = config.PROJECT_ID

def initialize_bigquery_client():
    try:
        return bigquery.Client()
    except FileNotFoundError:
        print("Warning: Using less secure Application Default Credentials (ADC).")
        return bigquery.Client()

def logout():
    st.session_state.clear()

def create_user(username, password):
    try:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        bq_client = initialize_bigquery_client()
        query = f"""
        INSERT INTO `{project_id}.bodysyncusers.user_info` (username, password)
        VALUES ('{username}', '{hashed_password}')
        """
        query_job = bq_client.query(query)
        query_job.result()
        return True
    except Exception as e:
        st.error(f"Error registering user: {e}")
        return False

def verify_user(username, password):
    try:
        bq_client = initialize_bigquery_client()
        query =  f"""
            SELECT password
            FROM `{project_id}.bodysyncusers.user_info`
            WHERE username = @username
        """
        query_params = [bigquery.ScalarQueryParameter("username", "STRING", username)]
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        query_job = bq_client.query(query, job_config=job_config)
        results = list(query_job.result())
        if results:
            stored_password = results[0]['password']
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if hashed_password == stored_password:
                return True
    except Exception as e:
        st.error(f"Error logging in: {e}")
    return False

def show_login_signup_forms():
    # Menu options
    menu = ["Login", "Sign Up"]
    choice = st.selectbox("Select one option ▾", menu)

    # Default choice
    if choice == "":
        st.subheader("Login")

    # Login option
    elif choice == "Login":
        st.write("-------")
        st.subheader("Log-In")
        with st.form('Login'):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button('Login')
            
            if login_button:
                if verify_user(username, password):
                    st.session_state["username"] = username
                    st.success("Logged in successfully!")
                    time.sleep(1)
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    
    # Sign Up option
    elif choice == "Sign Up":
        st.write("-----")
        st.subheader("Create New Account")
        with st.form('Create New Account'):
            new_username = st.text_input("Username", placeholder="Enter your username")
            new_password = st.text_input("Password", type="password", placeholder="Enter your password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            signup_button = st.form_submit_button('Sign Up')
            
            if signup_button:
                if new_password != confirm_password:
                    st.error("Passwords do not match. Please try again.")
                else:
                    if create_user(new_username, new_password):
                        st.success("Sign up successful. Please wait while we log you in...")
                        st.balloons()
                        time.sleep(3)  # Introduce a delay to allow signup process to complete
                        if verify_user(new_username, new_password):
                            st.session_state["username"] = new_username
                            st.session_state["logged_in"] = True
                            st.rerun()
                        else:
                            st.error("Automatic login failed. Please login manually.")
                    else:
                        st.error("Failed to sign up. Please try again.")

def main():
    logo_path = "https://github.com/alishuhh/body_sync/blob/main/misc/bodysync_logo.png?raw=true"
    # Center the image horizontally
    st.markdown(f"""
    <div style='text-align: center;'>
        <img src='{logo_path}' width='300'>
    </div>
     <p style="text-align: center; color: #F0F0F0; font-family: 'Roboto', sans-serif; font-size: 18px;">
                Your AI Fitness and Nutrition Companion
            </p>
    <hr style="border: 1px solid #F0F0F0;">
    """, unsafe_allow_html=True)
        
    
    # st.markdown(
    # """<h1 style=" text-align: center; color: #3498DB; font-family: 'Roboto', sans-serif; font-size: 36px; padding-bottom: 0px; padding-top: 0px">BodySync</h1>
    # <h3 style="text-align: center; color: #F0F0F0; font-size: 18px;  padding-top: 0; margin-left: 170px; ">Your AI Fitness and Nutrition Companion 🏋️‍♂️</h3>""",
    # unsafe_allow_html=True
    # )

    if st.session_state.get("logged_in"):
        with st.sidebar:
            username = st.session_state.get("username")
            st.markdown(
            f"""
            <h1 style="text-align: center; color: #B044E1; font-family: 'Roboto', sans-serif; font-size: 36px; padding-bottom: 0px; padding-top: 0px;">
                Welcome 🏋️‍♂️{username}
            </h1>
            <hr style="border: 1px solid #F0F0F0;">
            """,
            unsafe_allow_html=True
            )

            menu = option_menu("", ["🏠 Home", "👤 Profile", "💪 Workouts", "🥗 Nutrition", "💬 FitBuddy AI"])

            if st.button("🚪 Logout"):
                logout()
                st.sidebar.success("Logged out successfully!")
                st.rerun()


        if menu == "🏠 Home":
            home_page(st.session_state.get("username"), None)
        elif menu == "👤 Profile":
            profile_page(st.session_state.get("username"), None)
        elif menu == "💪 Workouts":
            workouts_page(st.session_state.get("username"), None)
        elif menu == "🥗 Nutrition":
            nutrition_page(st.session_state.get("username"), None)
        elif menu == "💬 FitBuddy AI":
            chat_page(st.session_state.get("username"), None)
        
        

        st.sidebar.write("")  # Add space between navigation and logout button
    
    else:
        show_login_signup_forms()

if __name__ == "__main__":
    main()
