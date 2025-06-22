import sqlite3
import hashlib
import streamlit as st
from streamlit import session_state as state
from datetime import date, timedelta, datetime
import time
import openai
from openai import OpenAI, RateLimitError, OpenAIError
import numpy as np
from PIL import Image
from io import BytesIO
import json
import requests
from pathlib import Path
import os
from sqlalchemy import text
from supabase import create_client, Client
import bcrypt
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------- Recipes Functions --------------------
def insert_recipe(recipe):
    data = {
        "title": recipe['title'],
        "image_url": recipe['image'],
        "diet": json.dumps(recipe['diet']),
        "ingredients": json.dumps(recipe['ingredients']),
        "calories": recipe['calories'],
        "macros": json.dumps(recipe['macros']),
        "instructions": recipe['instructions']
    }
    res = supabase.table("recipes").insert(data).execute()
    st.write(dir(res))
    if getattr(res, "status_code", None) != 201:
        raise Exception(f"Failed to insert recipe: {res}")

def get_all_recipes():
    res = supabase.table("recipes").select("*").execute()
    recipes = []
    for row in res.data:
        recipes.append({
            "title": row["title"],
            "image": row["image_url"],
            "diet": json.loads(row["diet"]) if row.get("diet") else [],
            "ingredients": row["ingredients"] if isinstance(row["ingredients"], dict) else json.loads(row["ingredients"]),
            "calories": row["calories"],
            "macros": row["macros"] if isinstance(row["macros"], dict) else json.loads(row["macros"]),
            "instructions": row["instructions"]
        })
    return recipes
        
# -------------------- Open AI --------------------
openai.api_key = st.secrets["openai"]["api_key"]
client = OpenAI(api_key=openai.api_key)

# -------------------- Calories Formula --------------------
def calories_formula(height, weight, age, gender, activity_level, goal=None):
    """Calculates daily caloric needs based on Mifflin-St Jeor Equation."""
    if gender == 'male':
        s=5
    elif gender== 'female':
        s=-161
    else:
        s=0

    BMI = (10*weight + 6.25*height - 5.0*age) + s

    if activity_level == 'Sedentary':
        activity_multiplier = 1.2
    elif activity_level == 'Lightly active':
        activity_multiplier = 1.375
    elif activity_level == 'Moderately active':
        activity_multiplier = 1.55
    elif activity_level == 'Very active':
        activity_multiplier = 1.725
    elif activity_level == 'Super active':
        activity_multiplier = 1.9
    
    calories= BMI * activity_multiplier

    if goal == 'Lose weight':
        additional=calories * (-0.15)
    elif goal == 'Maintain weight':
        additional=0
    elif goal == 'Gain weight':
        additional=calories * 0.10
    
    daily_calories = calories + additional

    if daily_calories < 1200:  # Minimum
        st.warning("Your calculated daily calories are below the recommended minimum of 1200 kcal. Please consult a healthcare provider for personalized advice.")
    elif daily_calories > 4000:  # Maximum
        st.warning("Your calculated daily calories are above the recommended maximum of 4000 kcal. Please consult a healthcare provider for personalized advice.")

    return round(daily_calories)

# -------------------- Macros Formula --------------------
def macros_formula(daily_calories, goal):
    if goal == 'Lose weight':
        protein_ratio = 0.4
        fat_ratio = 0.3
        carb_ratio = 0.3
    elif goal == 'Maintain weight':
        protein_ratio = 0.25
        fat_ratio = 0.15
        carb_ratio = 0.6
    elif goal == 'Gain weight':
        protein_ratio = 0.3
        fat_ratio = 0.2
        carb_ratio = 0.5

    protein_calories = daily_calories * protein_ratio
    fat_calories = daily_calories * fat_ratio
    carb_calories = daily_calories * carb_ratio

    protein_grams = round(protein_calories / 4)
    fat_grams = round(fat_calories / 9)
    carb_grams = round(carb_calories / 4)

    return {
        'protein': protein_grams,
        'fat': fat_grams,
        'carbs': carb_grams
    }

# -------------------- Age Formula --------------------
def calculate_age(dob):
        """Calculates the age based on the date of birth."""
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

# -------------------- week start Formula --------------------
def get_current_week_start():
    today = date.today()
    start = today - timedelta(days=today.weekday())  # Monday
    return start

# -------------------- Password Formula --------------------
def hash_password(password):
    """Hashes a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

# ------------------- Aesthetic -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Marmelad&family=ABeeZee:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'ABeeZee', sans-serif !important;
    background-color: #f7f9fc;
}

h1, h2, h3, h4 {
    font-family: 'Marmelad', cursive !important;
    font-weight: 600;
}

section[data-testid="stSidebar"] h1, 
section[data-testid="stSidebar"] h2, 
section[data-testid="stSidebar"] h3 {
    color: #e6e6fa !important;
    font-family: 'Marmelad', cursive !important;
}

section[data-testid="stSidebar"] {
    background-color: #e6e6fa !important;
}

/* Sidebar Title Color */
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
    color: #4b2596 !important;
}

div[data-baseweb="radio"] label {
    font-weight: 500;
    color: #333;
    padding: 6px 12px;
    border-radius: 8px;
    margin-bottom: 6px;
    transition: background 0.2s ease;
}

div[data-baseweb="radio"] label:hover {
    background-color: #ebe6fa;
}

div[data-baseweb="radio"] input:checked + div {
    background-color: #4b2596 !important;
    color: white !important;
    border-radius: 8px;
}

hr {
    border: none;
    border-top: 1px solid #eee;
    margin: 1em 0;
}

button[kind="primary"] {
    background-color: #E0E0E0 !important;
    color: #6a5acd  !important;
    border-radius: 8px !important;
}

.stButton>button {
    background-color: #E0E0E0;
    color: #6a5acd;
    padding: 8px 20px;
    border-radius: 10px;
    border: none;
    font-weight: bold;
}

input, textarea, select {
    color: #000 !important;
    border-radius: 10px !important;
}

.stTextInput > div > div > input {
    background-color: #fff;
    border: 1px solid #ccc;
    padding: 10px;
}

.stSelectbox > div {
    padding: 4px 10px;
}

div[data-testid="stExpander"] > details {
    background-color: #D9F2F1E8;
    border-radius: 10px;
    padding: 8px;
}

.stMarkdown code {
    background-color: #f2f2f2;
    border-radius: 6px;
    padding: 2px 6px;
}
</style>
""", unsafe_allow_html=True)

# -------------------- Sign In page --------------------
LOGO_TITLE = Path("./bodari_logo.png")
LOGO_IMAGE= Path("./bodari_logo_main.png")

def sign_in():
    # ------------- aesthetic ---------
    st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Audrey&family=Poppins&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Poppins', 'Audrey', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True
    )
    
    # Show logo at top
    col_image, col_title = st.columns([3,7])
    if LOGO_TITLE.exists() and LOGO_IMAGE.exists():
        with col_image:
            st.image(str(LOGO_IMAGE), width=300)  # adjust width for aesthetic
        with col_title:
            st.image(str(LOGO_TITLE), width=300)

    email = st.text_input("Email", placeholder="user@example.com")
    password = st.text_input("Password", type="password", placeholder="Enter your password")

    if st.button("Let's start"):
        res = supabase.table("users").select("id, password").eq("email", email).execute()
        user = res.data[0] if res.data else None

        if user:
            user_id = user['id']
            hashed_password = user['password']
            
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                st.session_state['user_id'] = user_id
                st.session_state['email'] = email
                st.session_state['page'] = 'main'
                st.success("Sign-in successful! Redirecting...")
            else:
                st.error("Incorrect password. Please try again.")
        else:
            st.warning("Email not found. Redirecting to create account...")
            st.session_state['email'] = email
            st.session_state['page'] = 'create_account'

# -------------------- Create Account page --------------------
def create_account():
    # ------------- aesthetic ---------
    st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Audrey&family=Poppins&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Poppins', 'Audrey', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True
    )

    # Show logo at top
    col_image, col_title = st.columns([3,7])
    if LOGO_TITLE.exists() and LOGO_IMAGE.exists():
        with col_image:
            st.image(str(LOGO_IMAGE), width=300)  # adjust width for aesthetic
        with col_title:
            st.image(str(LOGO_TITLE), width=300)

    email = st.text_input("Email", value=st.session_state.get('email', ''), placeholder="user@example.com")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")

    if st.button("Create Account"):
        if password != confirm_password:
            st.error("Passwords do not match. Please try again.")
            return
            
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
        try:
            res = supabase.table('users').insert({
                'email': email,
                'password': hashed_password
            }).execute()
            
            if res.data:
                user_id = res.data[0]['id'] 
                st.session_state['user_id'] = user_id
                st.session_state['page'] = 'onboarding'
                st.success("Account created successfully! Redirecting to onboarding...")
            else:
                st.error("Failed to create account. Please try again.")
        except Exception as e:
            if 'duplicate key' in str(e).lower():
                st.error("An account with this email already exists. Please sign in.")
            else:
                st.error(f"An error occurred: {e}")


# -------------------- Onboarding page --------------------

def onboarding():
    # ------------- aesthetic ---------
    st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Audrey&family=Poppins&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Poppins', 'Audrey', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True
    )

    col_image, col_title = st.columns([3,7])
    if LOGO_TITLE.exists() and LOGO_IMAGE.exists():
        with col_image:
            st.image(str(LOGO_IMAGE), width=300)  # adjust width for aesthetic
        with col_title:
            st.image(str(LOGO_TITLE), width=300)

    # Check login
    user_id = st.session_state.get('user_id')
    email = st.session_state.get('email')
    if not user_id:
        st.error("User not signed in. Redirecting to sign-in...")
        st.session_state['page'] = 'sign_in'
        return

    # Avoid duplicate onboarding
    res = supabase.table('user_account').select('*').eq('user_id', user_id).execute()
    profile = res.data[0] if res.data else None

    if profile:
        st.info("Profile already exists. Redirecting to the main page...")
        st.session_state['page'] = 'main'
        return

    # Collect user info
    name = st.text_input('How should I call you?')
    dob = st.date_input('Date of Birth', min_value=date(1900, 1, 1), max_value=date.today(), value=date(1990, 1, 1))
    height = st.number_input('Height (cm)', min_value=50, max_value=250, value=170)
    gender = st.selectbox( 'Gender', ['Male','Female'])
    weight = st.number_input('Weight (kg)', min_value=20, max_value=300, value=70)
    activity_level = st.selectbox('Activity Level', ['Sedentary', 'Lightly active', 'Moderately active', 'Very active', 'Super active'])
    goal = st.selectbox('Goal', ['Lose weight', 'Maintain weight', 'Gain weight'])
    timeline = st.number_input('Timeline (weeks)', min_value=1, max_value=52, value=12)
    dietary_restrictions = st.multiselect(
        'Dietary Restrictions',
        ['Vegetarian', 'Vegan', 'Gluten-free', 'Dairy-free', 'Nut-free', 'None']
    )

    # Save profile
    if st.button("Save Profile"):
        dietary_restrictions_str = ','.join(dietary_restrictions)
        data = {
            'user_id': user_id,
            'name': name,
            'dob': dob.isoformat(),
            'gender': gender,
            'height': height,
            'weight': weight,
            'activity_level': activity_level,
            'goal': goal,
            'timeline': timeline,
            'dietary_restrictions': dietary_restrictions_str
        }
        
        res = supabase.table('user_account').insert(data).execute()
        
        if res.data:
            st.success("User profile saved successfully.")
        else:
            st.error(f"Failed to save user profile. Response:{res}")

        st.success("✅ Profile saved! Redirecting to the main page...")
        st.session_state['page'] = 'main'

# -------------------- Main page --------------------
def main_page():
# ------------- aesthetic ---------
    st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Audrey&family=Poppins&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Poppins', 'Audrey', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True
    )
    
    col1,col2=st.columns([2,8])
    with col1:
        st.image(str(LOGO_IMAGE), width=300)
    with col2:
        st.image(str(LOGO_TITLE), width=300)
    
    tab1, tab2, tab3 , tab4 , tab5 = st.tabs(['Main', 'Recipes', 'Groceries', 'Image Recognition', 'Fitbit App'])
    with tab1:

        user_id = st.session_state.get('user_id')
        email = st.session_state.get('email')

        try:
            user_id_int = int(user_id)
        except Exception:
            st.error("Invalid user_id in session state.")
            st.session_state['page'] = 'sign_in'
            return

        # Display user profile
        res = supabase.table('user_account').select('*').eq('user_id', user_id).execute()

        if res.data and len(res.data) > 0:
            profile = res.data[0]  # One profile expected
        else:
            profile = None
            st.warning("Profile not found or error fetching profile.")
        
        if not profile:
            st.warning("Profile not found. Please complete onboarding.")
            st.session_state['page'] = 'onboarding'
            return
        
        id = profile.get('id')
        name = profile.get('name')
        dob = profile.get('dob')
        gender = profile.get('gender')
        height = profile.get('height')
        weight = profile.get('weight')
        activity_level = profile.get('activity_level')
        goal = profile.get('goal')
        timeline = profile.get('timeline')
        dietary_restrictions = profile.get('dietary_restrictions')
        dietary_restrictions_list = dietary_restrictions.split(',') if dietary_restrictions else []

        # Ensure dob is a date object
        if isinstance(dob, str):
            dob = datetime.strptime(dob, "%Y-%m-%d").date()
        
        age = calculate_age(dob)

        row1_col1, row1_col2 = st.columns([6, 2])
        with row1_col1:
            st.markdown(f"## Hello, {name}!")
        with row1_col2:
            if st.button("➕ Add Meal"):
                st.session_state["show_add_meal_form"] = True

        if st.session_state.get("show_add_meal_form", False):
            st.markdown("### Add a Meal You Ate")
            with st.form("add_meal_form"):
                meal_name = st.text_input("Meal name (e.g. Chicken Wrap, Pasta Bowl)")
                ingredients_raw = st.text_area("Ingredients and quantities. Please input in the following structure - **ingredient: quantity**")
                meal_date = st.date_input("Date", value=date.today())
                submitted = st.form_submit_button("Save Meal")

                if submitted:
                    if not meal_name or not ingredients_raw:
                        st.error("Please fill in all fields.")
                        st.stop()

                    # Parse ingredients
                    ingredients = {}
                    for line in ingredients_raw.strip().split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            ingredients[k.strip()] = v.strip()
                            
                    if not ingredients:
                        st.error("Please provide at least one valid ingredient with quantity, e.g. 'Chicken: 150g'")
                        st.stop()
                    # Create OpenAI prompt
                    prompt = f"""Estimate the total protein (g), fat (g), carbs (g), and calories for a meal made of the following ingredients:
                    """
                    for ing, qty in ingredients.items():
                        prompt += f"- {ing}: {qty}\n"
                    
                    prompt += """
                    Please respond in the following format:
                    Protein: XXg  
                    Fat: XXg  
                    Carbs: XXg  
                    Calories: XXX
                    
                    Example:
                    Protein: 30g  
                    Fat: 15g  
                    Carbs: 40g  
                    Calories: 500
                    """
                    
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": "You are a nutritionist assistant that estimates macronutrients."},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        reply = response.choices[0].message.content
                        # Example reply: "Protein: 35g, Fat: 12g, Carbs: 40g, Calories: 480"

                        import re
                        def extract_macro(name, text):
                            pattern = rf"({name})[:\-]?\s*(\d+(?:\.\d+)?)\s*g?"
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match and match.group(2) is not None:
                                print(f"Extracted {name}: {match.group(2)}")
                                return float(match.group(2))
                            else:
                                print(f"Failed to extract {name}")
                                return 0.0
                        
                        protein = extract_macro("protein", reply)
                        fat = extract_macro("fat", reply)
                        carbs = extract_macro("carbs|carbohydrates", reply)
                        calories = extract_macro("calories", reply)
                        
                        # Save to DB
                        data = {
                            'user_id': user_id,
                            'date': meal_date.isoformat() if hasattr(meal_date, 'isoformat') else meal_date,
                            'meal_name': meal_name,
                            'ingredients': json.dumps(ingredients),
                            'protein': protein,
                            'fat': fat,
                            'carbs': carbs,
                            'calories': calories
                        }
                        
                        res = supabase.table('user_meals').insert(data).execute()
                        
                        if res.data:
                            st.success("Meal saved successfully!")
                        else:
                            st.error(f"Failed to save meal. Response: {res}")
    
                        st.success(f"Meal '{meal_name}' saved with estimated macros!")
                        st.session_state["show_add_meal_form"] = False
                        st.rerun()
                    except OpenAIError as e:
                        st.error(f"OpenAI estimation failed: {e}")
                        return
                        
        st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)

        # Calculate daily calories and macros
        daily_calories = calories_formula(height, weight, age, gender, activity_level, goal)
        macros = macros_formula(daily_calories, goal)

        # --- Calculate Consumed Calories and Macros ---
        res = supabase.table('user_meals') \
            .select('protein, fat, carbs, calories') \
            .eq('user_id', user_id) \
            .eq('date', date.today().isoformat()) \
            .execute()
        
        today_meals = res.data if res.data else []
        
        consumed = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}
        for meal in today_meals:
            consumed['protein'] += meal.get('protein', 0) or 0
            consumed['fat'] += meal.get('fat', 0) or 0
            consumed['carbs'] += meal.get('carbs', 0) or 0
            consumed['calories'] += meal.get('calories', 0) or 0

        remaining = {
            'calories': max(daily_calories - consumed['calories'], 0),
            'protein': max(macros['protein'] - consumed['protein'], 0),
            'fat': max(macros['fat'] - consumed['fat'], 0),
            'carbs': max(macros['carbs'] - consumed['carbs'], 0)
        }

        # --- Display Calories ---
        st.markdown(
        f"""
        <div style='font-size: 32px; color: #e57373; font-weight: bold; text-align: center;'>
            {consumed['calories']} kcal / {daily_calories} kcal
        </div>
        """,
        unsafe_allow_html=True
        )

        # --- Display Macros as Progress Bars ---
        
        # Set total macro sum for relative percentage bars
        total_macros = macros['protein'] + macros['fat'] + macros['carbs']

        # Function to render a macro bar
        def macro_bar(name, total, consumed_val, remaining_val, color):
            st.markdown(
                f"""
                <div style='margin-bottom: 14px;'>
                    <div style='font-weight: 500; margin-bottom: 4px;'>{name}</div>
                    <div style='background-color: #e0e0e0; border-radius: 10px; height: 20px; width: 100%; position: relative;'>
                        <div style='width: {min(consumed_val/total*100 if total else 0,100)}%; background-color: {color}; height: 100%; border-radius: 10px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-size: 14px;'>
                            {consumed_val}g
                        </div>
                        <div style='position: absolute; right: 8px; top: 0; height: 100%; display: flex; align-items: center; color: #4b2596; font-size: 14px;'>
                            {remaining_val}g
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True
            )

        macro_bar("Protein", macros['protein'], consumed['protein'], remaining['protein'], "#4b2596")
        macro_bar("Fat", macros['fat'], consumed['fat'], remaining['fat'], "#14b3ad")
        macro_bar("Carbs", macros['carbs'], consumed['carbs'], remaining['carbs'], "#fbad05")

        # -------------------- Pantry Ingredients Section --------------------
        st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
        st.markdown("### What's in your pantry?")
        st.markdown("Select the ingredients you currently have. You can optionally specify the quantity and unit for each.")

        # Define a list of common ingredients to select from
        common_ingredients = [
            "Eggs", "Milk", "Cheese", "Bread", "Spinach", "Chicken Breast", "Rice", "Oats",
            "Banana", "Apple", "Tomato", "Carrot", "Potato", "Yogurt", "Beans", "Lentils", "Broccoli"
        ]

        selected_ingredients = st.multiselect("Select available ingredients", options=common_ingredients, key="pantry_ingredients")

        pantry_data = []
        for ingredient in selected_ingredients:
            with st.expander(f"{ingredient} details"):
                quantity = st.number_input(f"Quantity of {ingredient}", min_value=0.0, step=10.0, format="%.2f", key=f"{ingredient}_qty")
                unit = st.selectbox(f"Unit for {ingredient}", ["grams", "kg", "ml", "liters", "cups", "pieces"], key=f"{ingredient}_unit")
                pantry_data.append((user_id, date.today(), ingredient, quantity if quantity > 0 else None, unit if quantity > 0 else "units"))

        if st.button("Save Pantry"):
            for entry in pantry_data:
                data = {
                    'user_id': entry[0],
                    'date': entry[1].isoformat() if hasattr(entry[1], 'isoformat') else entry[1],
                    'ingredient': entry[2],
                    'quantity': entry[3],
                    'unit': entry[4]
                }
                res = supabase.table('grocery_ingredients').upsert(data).execute()
                if not res.data:
                    st.error(f"Error saving {entry[2]}. Response: {res}")
                else:
                    st.success("Pantry ingredients saved successfully!")
                st.markdown("<br>", unsafe_allow_html=True)
        
        # -------------------- Weekly Meal Plan Section --------------------
        st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
        st.markdown("### Weekly Meal Plan")
        st.markdown("Let's create a weekly meal plan tailored to your needs:")

        week_start = get_current_week_start()
        today_str = date.today().isoformat()
        
        # 1. Fetch pantry ingredients added within the current week
        res = supabase.table('grocery_ingredients') \
            .select('ingredient, quantity, unit, date') \
            .eq('user_id', user_id) \
            .gte('date', week_start.isoformat()) \
            .execute()
        
        pantry_rows = res.data if res.data else []
        
        # 2. Check if any pantry entry was added today
        pantry_updated_today = any(row.get('date') == today_str for row in pantry_rows)
        
        # 3. Build pantry string for AI only from valid entries this week
        pantry_ingredients_str = "\n".join([
            f"{row['ingredient']} ({row['quantity']} {row['unit']})"
            for row in pantry_rows if row.get('quantity')
        ])
        
        # 4. Check for cached meal plan
        res = supabase.table('weekly_meal_plan') \
            .select('meal_plan') \
            .eq('user_id', user_id) \
            .eq('week_start', week_start.isoformat()) \
            .limit(1) \
            .execute()
        
        meal_plan = res.data[0]['meal_plan'] if res.data else None
        
        # 5. Main logic: only regenerate meal plan if pantry was updated today
        if meal_plan and not pantry_updated_today:
            weekly_meal_plan = meal_plan
        else:
            # Compose the prompt
            prompt = f"""
            The user has the following dietary restrictions: {dietary_restrictions_list} and needs to consume {daily_calories} calories daily with the following macros composition in grams: {macros}.
            """
        
            if pantry_ingredients_str:
                prompt += f"\nThe user currently has the following ingredients available in their pantry: {pantry_ingredients_str}. Try to incorporate them into the meal plan when possible, but you can also use other ingredients to complete the meals."
        
            prompt += """
            Please create a weekly meal plan with breakfast, lunch, dinner, and two snacks for each day of the week. 
            Add the weight of each ingredient for each meal. 
            The meal plan should be healthy, balanced, and diverse, and meet the user's dietary restrictions and caloric needs.
            Present the plan in a table format with columns for each meal and rows for the days of the week (Monday to Sunday). 
            Each cell should include the meal description with ingredients and their quantities.
            """
        
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a nutritionist assistant that creates healthy and balanced weekly meal plans."},
                        {"role": "user", "content": prompt}
                    ]
                )
                weekly_meal_plan = response.choices[0].message.content.strip()
        
                # Save/update plan
                res = supabase.table('weekly_meal_plan').upsert({
                    'user_id': user_id,
                    'week_start': week_start.isoformat(),
                    'meal_plan': weekly_meal_plan
                }).execute()
        
                if not res.data:
                    st.error(f"Failed to save weekly meal plan. Response: {res}")
        
            except RateLimitError:
                st.warning("Rate limit reached. Waiting for 20 seconds before retrying...")
                time.sleep(20)
                return
            except OpenAIError as e:
                st.error(f"Error in creating your weekly meal plan with OpenAI: {e}")
                return
        
        # Show plan
        st.markdown(weekly_meal_plan)


        st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
        st.markdown("### Logged Meals")

        res = supabase.table('user_meals') \
            .select('date, meal_name, protein, fat, carbs, calories') \
            .eq('user_id', user_id) \
            .order('date', desc=True) \
            .execute()
        
        
        meals = res.data if res.data else []

        if not meals:
            st.info("You haven’t added any meals yet.")
        else:
            for meal in meals:
                m_date = meal.get('date')
                name = meal.get('meal_name')
                p = meal.get('protein', 0)
                f = meal.get('fat', 0)
                c_ = meal.get('carbs', 0)
                cal = meal.get('calories', 0)
                st.markdown(f"**{m_date} – {name}**")
                st.markdown(f"- Protein: {p}g | Fat: {f}g | Carbs: {c_}g | Calories: {cal} kcal")


# -------------------- Recipes Page--------------------
    with tab2:

        # Title and Add Recipe button aligned right
        cols = st.columns([8, 2])
        cols[0].title("Recipe Finder")
        add_clicked = cols[1].button("➕ Add Recipe")

        if add_clicked or st.session_state.get("show_add_recipe_form", False):
            st.session_state["show_add_recipe_form"] = True
            st.subheader("Add a New Recipe")

            with st.form("add_recipe_form"):
                title = st.text_input("Recipe Title")
                image_file = st.file_uploader("Upload an image for the recipe", type=["png", "jpg", "jpeg"])
                diet_options = ['Vegetarian', 'Vegan', 'Gluten-free', 'Dairy-free', 'Nut-free', 'None']
                diet = st.multiselect("Dietary Preferences", diet_options)
                
                st.markdown("### Ingredients (enter as `Ingredient: Quantity`)")
                ingredients_raw = st.text_area(
                    "List ingredients separated by newline, e.g.:\nChicken Breast: 150g\nSpinach: 50g"
                )

                calories = st.number_input("Calories (kcal)", min_value=0)
                protein = st.number_input("Protein (g)", min_value=0)
                fat = st.number_input("Fat (g)", min_value=0)
                carbs = st.number_input("Carbs (g)", min_value=0)
                instructions = st.text_area("Instructions")

                col_submit, col_exit = st.columns([1,1])
                submitted = col_submit.form_submit_button("Save Recipe")
                exit_clicked = col_exit.form_submit_button("Exit")

                if exit_clicked:
                    st.session_state["show_add_recipe_form"] = False
                    st.rerun()

                if submitted:
                    if not title:
                        st.error("Please enter a recipe title.")
                        st.stop()
                    if not image_file:
                        st.error("Please upload an image.")
                        st.stop()

                    # Parse ingredients
                    ingredients = {}
                    for line in ingredients_raw.split("\n"):
                        if ':' in line:
                            key, val = line.split(':', 1)
                            ingredients[key.strip()] = val.strip()

                    # Save uploaded image locally
                    upload_dir = Path("uploaded_images")
                    upload_dir.mkdir(exist_ok=True)
                    
                    file_extension = image_file.name.split('.')[-1]
                    safe_title = "".join(x for x in title if x.isalnum() or x in (" ", "_")).rstrip()
                    filename = f"{safe_title}.{file_extension}"
                    filepath = upload_dir / filename
                    
                    with open(filepath, "wb") as f:
                        f.write(image_file.getbuffer())
                    
                    image_path = str(filepath)

                    new_recipe = {
                        "title": title,
                        "image": image_path,  # local image path
                        "diet": diet,
                        "ingredients": ingredients,
                        "calories": calories,
                        "macros": {
                            "protein": protein,
                            "fat": fat,
                            "carbs": carbs
                        },
                        "instructions": instructions
                    }

                    insert_recipe(new_recipe)

                    st.success("Recipe added successfully!")
                    st.session_state["show_add_recipe_form"] = False
                    st.rerun()

        else:
            with st.container():
                with st.expander(" Filters ", expanded=True):
                    all_diet_types = ['Vegetarian', 'Vegan', 'Gluten-free', 'Dairy-free', 'Nut-free', 'None']
                    selected_diets = st.multiselect("Select dietary preferences", all_diet_types)

                    all_ingredients = [
                        "Eggs", "Milk", "Cheese", "Bread", "Spinach", "Chicken Breast", "Rice", "Oats",
                        "Banana", "Apple", "Tomato", "Carrot", "Potato", "Yogurt", "Beans", "Lentils", "Broccoli"
                    ]
                    selected_ingredients = st.multiselect("Select available ingredients", all_ingredients, key="recipe_filter_ingredients")

            st.markdown("""<hr style='border:1px solid #ddd; margin:20px 0;'>""", unsafe_allow_html=True)

            recipes = get_all_recipes()

            def matches_filters(recipe):
                if selected_diets:
                    diet_ok = any(d in recipe['diet'] for d in selected_diets if d != "None")
                else:
                    diet_ok = True
                    
                if selected_ingredients:
                    ingredient_ok = any(ing in recipe['ingredients'] for ing in selected_ingredients)
                else:
                    ingredient_ok = True
            
                return diet_ok and ingredient_ok

            # Determine if filters are active
            filters_active = bool(selected_diets or selected_ingredients)

            def render_recipe(recipe):
                with st.container():
                    st.markdown(
                        """
                        <div style="display: flex; gap: 20px; padding: 16px; border-radius: 16px; 
                                    background-color: #FBD89A; box-shadow: 0 2px 8px rgba(0,0,0,0.05); 
                                    margin-bottom: 20px;">
                        """, unsafe_allow_html=True
                    )
            
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        try:
                            if recipe['image'] and os.path.exists(recipe['image']):
                                img = Image.open(recipe['image'])
                                st.image(img, use_column_width=True)
                            else:
                                img_data = requests.get(recipe['image']).content
                                img = Image.open(BytesIO(img_data))
                                st.image(img, use_column_width=True)
                        except Exception:
                            st.warning("Image could not be loaded.")
            
                    with col2:
                        st.markdown(f"<h4 style='margin-bottom: 0;'>{recipe['title']}</h4>", unsafe_allow_html=True)
                        st.markdown(f"<div style='color: gray;'>Calories: {recipe['calories']} kcal</div>", unsafe_allow_html=True)
                        st.markdown(
                            f"""
                            <div style='margin: 8px 0;'>
                            <strong>Macros:</strong> 
                            {recipe['macros']['protein']}g protein, 
                            {recipe['macros']['fat']}g fat, 
                            {recipe['macros']['carbs']}g carbs
                            </div>
                            """, unsafe_allow_html=True
                        )
                        with st.expander("More Information"):
                            st.markdown("**Ingredients:**")
                            for ing, qty in recipe['ingredients'].items():
                                st.markdown(f"- {ing}: {qty}")
                            st.markdown("**Instructions:**")
                            st.markdown(recipe['instructions'])
            
                    st.markdown("</div>", unsafe_allow_html=True)
            
            # Apply filtering if filters are active
            if filters_active:
                filtered_recipes = [r for r in recipes if matches_filters(r)]
            
                if not filtered_recipes:
                    st.warning("No recipes found for selected filters.")
                else:
                    for recipe in filtered_recipes:
                        render_recipe(recipe)
            else:
                for recipe in recipes:
                    render_recipe(recipe)
                    
# -------------------- Groceries Page--------------------
    with tab3:
        st.header("Grocery List for This Week")
        
        week_start = get_current_week_start()
    
        # Fetch the weekly meal plan
        res = supabase.table('weekly_meal_plan') \
            .select('meal_plan') \
            .eq('user_id', user_id) \
            .eq('week_start', week_start.isoformat()) \
            .limit(1) \
            .execute()
    
        if not res.data:
            st.warning("You don't have a meal plan for this week yet.")
            st.stop()
    
        meal_plan_text = res.data[0]['meal_plan']
    
        # --- Extract ingredients from meal plan ---
        from collections import defaultdict
        import re
        
        ingredient_counts = defaultdict(float)
        
        # Extract all lines that look like ingredient(quantity)
        matches = re.findall(r'([\w\s]+)\s*\((\d+(?:\.\d+)?)\s*(g|ml)?\)', meal_plan_text)
        
        for name, qty, unit in matches:
            normalized_name = name.strip().lower()
            amount = float(qty)
            if unit == "ml":
                # Optionally treat ml differently if needed
                pass
            ingredient_counts[normalized_name] += amount
    
        # --- Get pantry ingredients added this week ---
        pantry_res = supabase.table('grocery_ingredients') \
            .select('ingredient') \
            .eq('user_id', user_id) \
            .gte('date', week_start.isoformat()) \
            .execute()
        
        pantry_items = [row['ingredient'].strip().lower() for row in pantry_res.data] if pantry_res.data else []
    
        # --- Compute grocery list ---
        grocery_items = {
            k: v for k, v in ingredient_counts.items()
            if k not in pantry_items
        }

    
        if not grocery_items:
            st.success("🎉 Your pantry is fully stocked for this week's meals!")
        else:
            st.markdown("Here’s what you still need to buy:")
            checked = []
            for item, qty in grocery_items.items():
                if st.checkbox(f"{item.title()} – {round(qty)}g", key=f"grocery_{item}"):
                    checked.append(item)
            if checked:
                st.success(f"You marked {len(checked)} item(s) as bought.")





# -------------------- Image Recognition Tab --------------------    
    with tab4:
        # Inject custom CSS styling directly inside the tab block.
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Marmelad&family=ABeeZee:wght@300;400;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'ABeeZee', sans-serif !important;
            background-color: #f7f9fc;
            text-align: center;
        }

        main {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        h1, h2, h3, h4 {
            font-family: 'Marmelad', cursive !important;
            font-weight: 600;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.header("Image Recognition 🔍")
        
        # Image uploader for the ticket image
        uploaded_image = st.file_uploader("📸 Upload your ticket image", type=["jpg", "jpeg", "png"])
        
        if uploaded_image is not None:
            image = Image.open(uploaded_image)
            # Display image with a fixed width (using 'width' as use_container_width replacement)
            st.image(image, caption="Your Ticket 🎫", width=300)
        
        # Start analysis on button click
        if st.button("Analyze 🔎"):
            st.write("Analyzing your image... ⏳")
            progress_bar = st.progress(0)
            for i in range(101):
                time.sleep(3 / 100)  # Simulate a 3-second progress
                progress_bar.progress(i)
            
            # Predefined list of products from the ticket
            data = [
                {"Producto": "Huevo fresco M DO", "Cantidad": 1},
                {"Producto": "Pizza maxi barbacoa", "Cantidad": 1},
                {"Producto": "Jamón 250+250", "Cantidad": 1},
                {"Producto": "Entrecot de añojo", "Cantidad": 1},
                {"Producto": "Agua Font Vella 1L", "Cantidad": 1},
                {"Producto": "Aceituna rellena suave", "Cantidad": 1},
                {"Producto": "Patatas campesinas", "Cantidad": 1},
                {"Producto": "Aceituna negra", "Cantidad": 2},
                {"Producto": "Postre leche B. Easo 350g", "Cantidad": 1},
                {"Producto": "Pan sin corteza Bimbo 610g", "Cantidad": 1},
                {"Producto": "Leche botella entera Asturiana", "Cantidad": 2},
                {"Producto": "Torta imperial", "Cantidad": 1},
                {"Producto": "Turrón duro Calidad Suprema", "Cantidad": 3},
                {"Producto": "Turrón blando Calidad Suprema", "Cantidad": 3},
                {"Producto": "Turrón yema tostada", "Cantidad": 1},
                {"Producto": "Vino tinto crianza C. Colegia", "Cantidad": 1},
                {"Producto": "Jabón Magno", "Cantidad": 1},
                {"Producto": "Bolsa Eroski OXO", "Cantidad": 4}
            ]
            df = pd.DataFrame(data)
            # Filter out non-food items (assuming "Jabón Magno" and "Bolsa Eroski OXO" are non-food)
            food_items = df[~df["Producto"].isin(["Jabón Magno", "Bolsa Eroski OXO"])]
            
            st.markdown("### Identified Food Items 🍏")
            # Display a more nicely designed table using st.dataframe
            st.dataframe(food_items.reset_index(drop=True), width=600, height=300)
            
            # Final summary message with fixed text
            st.markdown("<h3>22 productos added to your pantry 🎉</h3>", unsafe_allow_html=True)



# -------------------- Fitbit Dashboard Tab --------------------


    with tab5:
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Marmelad&family=ABeeZee:wght@300;400;600&display=swap');

            html, body, [class*="css"] {
                font-family: 'ABeeZee', sans-serif !important;
                background-color: #f7f9fc;
                text-align: center;
            }

            main {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }

            h1, h2, h3, h4 {
                font-family: 'Marmelad', cursive !important;
                font-weight: 600;
            }
            </style>
            """, unsafe_allow_html=True)
        
        st.header("Fitbit Dashboard 🏃‍♂️")

        # -------------------------------------------------------------------------
        # Display the current day of the week.
        # -------------------------------------------------------------------------
        day_of_week = datetime.now().strftime("%A")
        st.subheader(f"Today is {day_of_week}")

        # -------------------------------------------------------------------------
        # Fake Data Generation for the Dashboard
        # -------------------------------------------------------------------------
        steps = np.random.randint(3000, 15000)
        steps_target = 10000

        kcal_burned = np.random.randint(1500, 3500)
        kcal_target = 2500

        times = pd.date_range(start=datetime.now().replace(hour=6, minute=0, second=0, microsecond=0), periods=12, freq='H')
        heart_rate = np.random.randint(60, 160, size=12)
        df_hr = pd.DataFrame({"Time": times, "Heart Rate": heart_rate})

        sleep_stages = ["Deep", "Light", "REM", "Awake"]
        sleep_hours = [np.random.uniform(1, 3), np.random.uniform(2, 4), np.random.uniform(1, 2), np.random.uniform(0.5, 1)]
        df_sleep = pd.DataFrame({"Stage": sleep_stages, "Hours": np.round(sleep_hours, 1)})

        dates = pd.date_range(end=datetime.now(), periods=7)
        weekly_steps = [np.random.randint(5000, 12000) for _ in range(7)]
        weekly_calories = [np.random.randint(2000, 3200) for _ in range(7)]
        weekly_active = [np.random.randint(30, 120) for _ in range(7)]
        weekly_sleep = [np.random.uniform(5, 8) for _ in range(7)]
        weekly_resting_hr = [np.random.randint(55, 75) for _ in range(7)]
        df_week = pd.DataFrame({
            "Date": dates,
            "Steps": weekly_steps,
            "Calories Burned": weekly_calories,
            "Active Minutes": weekly_active,
            "Sleep Hours": weekly_sleep,

        })

        # -------------------------------------------------------------------------
        # Charts in 2 Columns
        # -------------------------------------------------------------------------
        col1, col2 = st.columns(2)

        with col1:
            gauge_steps = go.Figure(go.Indicator(
                mode="gauge+number",
                value=steps,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Steps Walked 🚶‍♂️"},
                gauge={
                    'axis': {'range': [0, 15000]},
                    'bar': {'color': "#6a5acd"},
                    'steps': [
                        {'range': [0, steps_target], 'color': "#dcdcff"},
                        {'range': [steps_target, 15000], 'color': "#f3f3f3"}
                    ],
                }
            ))
            gauge_steps.update_layout(height=250, margin={'t': 50, 'b': 0})
            st.plotly_chart(gauge_steps, use_container_width=True)

        with col2:
            gauge_kcal = go.Figure(go.Indicator(
                mode="gauge+number",
                value=kcal_burned,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Calories Burned 🔥"},
                gauge={
                    'axis': {'range': [0, 3500]},
                    'bar': {'color': "#ff6347"},
                    'steps': [
                        {'range': [0, kcal_target], 'color': "#ffe4e1"},
                        {'range': [kcal_target, 3500], 'color': "#f3f3f3"}
                    ],
                }
            ))
            gauge_kcal.update_layout(height=250, margin={'t': 50, 'b': 0})
            st.plotly_chart(gauge_kcal, use_container_width=True)

        col3, col4 = st.columns(2)

        with col3:
            line_hr = px.line(df_hr, x="Time", y="Heart Rate", title="Heart Rate Over Day ❤️")
            st.plotly_chart(line_hr, use_container_width=True)

        with col4:
            bar_sleep = px.bar(df_sleep, x="Stage", y="Hours", title="Sleep Breakdown 😴", text="Hours", color="Stage")
            st.plotly_chart(bar_sleep, use_container_width=True)

        col5, col6 = st.columns(2)

        radar_categories = ["Endurance", "Strength", "Flexibility", "Speed", "Stamina"]
        radar_values = np.random.randint(50, 100, size=4).tolist()
        radar_values.append(radar_values[0])
        radar_categories.append(radar_categories[0])

        with col5:
            radar_chart = go.Figure()
            radar_chart.add_trace(go.Scatterpolar(
                r=radar_values,
                theta=radar_categories,
                fill='toself',
                name='Fitness Metrics',
                line=dict(color="#ff6347")
            ))
            radar_chart.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False,
                title="Overall Fitness Metrics 🔥"
            )
            st.plotly_chart(radar_chart, use_container_width=True)

        with col6:
            activity_labels = ["Sedentary", "Moderate", "Vigorous"]
            activity_values = [np.random.randint(300, 900), np.random.randint(200, 600), np.random.randint(100, 300)]
            pie_chart = px.pie(names=activity_labels, values=activity_values, title="Daily Activity Distribution")
            st.plotly_chart(pie_chart, use_container_width=True)

        # -------------------------------------------------------------------------
        # Weekly Summary Table (Keep in full width)
        # -------------------------------------------------------------------------
        st.markdown("### Weekly Summary 📅")
        st.dataframe(df_week.style.format({
            "Steps": "{:,}",
            "Calories Burned": "{:,}",
            "Active Minutes": "{:,}",
            "Sleep Hours": "{:.1f}",
        }), height=300)

        # -------------------------------------------------------------------------
        # Weekly Trends in 2-column layout
        # -------------------------------------------------------------------------
        st.markdown("#### Trends Over Last 7 Days")
        trends = [
            px.line(df_week, x="Date", y="Steps", title="Steps Trend"),
            px.line(df_week, x="Date", y="Calories Burned", title="Calories Burned Trend", markers=True),
            px.line(df_week, x="Date", y="Active Minutes", title="Active Minutes Trend"),
            px.line(df_week, x="Date", y="Sleep Hours", title="Sleep Hours Trend"),
        ]

        for i in range(0, len(trends), 2):
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(trends[i], use_container_width=True)
            if i + 1 < len(trends):
                with c2:
                    st.plotly_chart(trends[i + 1], use_container_width=True)



# -------------------- App Initialization --------------------

if 'page' not in st.session_state:
    st.session_state['page'] = 'sign_in'

if st.session_state['page'] == 'sign_in':
    sign_in()
elif st.session_state['page'] == 'create_account':
    create_account()
elif st.session_state['page'] == 'onboarding':
    onboarding()
elif st.session_state['page'] == 'main':
    main_page()
