import sqlite3
import hashlib
import streamlit as st
from streamlit import session_state as state
from datetime import date, time, timedelta
import openai
import numpy as np
from PIL import Image
from io import BytesIO
import json
import requests
from pathlib import Path
import os

def create_database():
    conn = sqlite3.connect('bodari_users.db')
    c = conn.cursor()
    
    # Create table to store users credentials
    c.execute('''
              CREATE TABLE IF NOT EXISTS users(
              id INTEGER PRIMARY KEY, 
              email TEXT UNIQUE, 
              password TEXT)
              ''')
    
    # Create table to store users account information
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_account (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            dob DATE,
            gender TEXT,
            height REAL NOT NULL,
            weight REAL NOT NULL,
            activity_level TEXT NOT NULL,
            goal TEXT NOT NULL,
            timeline INTEGER NOT NULL,
            dietary_restrictions TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create a table to store weekly grocery ingredients
    c.execute('''
        CREATE TABLE IF NOT EXISTS grocery_ingredients (
              user_id INTEGER NOT NULL,
              date DATE NOT NULL,
              ingredient TEXT NOT NULL,
              quantity REAL NOT NULL,  -- Quantity in grams
              unit TEXT NOT NULL,  -- e.g., grams, kg, cups
              PRIMARY KEY (user_id, date),
              FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create a tavle to store the weekly meal plan created
    c.execute('''
        CREATE TABLE IF NOT EXISTS weekly_meal_plan (
            user_id INTEGER NOT NULL,
            week_start DATE NOT NULL,
            meal_plan TEXT NOT NULL,
            PRIMARY KEY (user_id, week_start),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create a table to store recipes information
    c.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            image_url TEXT,
            diet TEXT,               -- JSON string list
            ingredients TEXT,        -- JSON dict string
            calories INTEGER,
            macros TEXT,             -- JSON dict string
            instructions TEXT
        )
    ''')

    # Create a table to log the user meals
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date DATE,
            meal_name TEXT,
            ingredients TEXT,         -- JSON string of {ingredient: quantity}
            protein REAL,
            fat REAL,
            carbs REAL,
            calories REAL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Save (commit) the changes
    conn.commit()
    
    # Close the connection
    conn.close()

# -------------------- Recipes Functions --------------------
def insert_recipe(recipe):
    conn = sqlite3.connect('bodari_users.db')
    c = conn.cursor()

    c.execute('''
        INSERT INTO recipes (title, image_url, diet, ingredients, calories, macros, instructions)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        recipe['title'],
        recipe['image'],
        json.dumps(recipe['diet']),
        json.dumps(recipe['ingredients']),
        recipe['calories'],
        json.dumps(recipe['macros']),
        recipe['instructions']
    ))

    conn.commit()
    conn.close()

def get_all_recipes():
    conn = sqlite3.connect('bodari_users.db')
    c = conn.cursor()
    c.execute("SELECT title, image_url, diet, ingredients, calories, macros, instructions FROM recipes")
    rows = c.fetchall()
    conn.close()

    recipes = []
    for row in rows:
        recipes.append({
            "title": row[0],
            "image": row[1],
            "diet": json.loads(row[2]),
            "ingredients": json.loads(row[3]),
            "calories": row[4],
            "macros": json.loads(row[5]),
            "instructions": row[6],
        })
    return recipes

def populate_mock_recipes():
    recipes = [
        {
            "title": "Grilled Chicken Salad",
            "image": "https://www.eatingbirdfood.com/wp-content/uploads/2023/06/grilled-chicken-salad-hero.jpg",
            "diet": ["Gluten-free"],
            "ingredients": {
                "Chicken Breast": "150g",
                "Spinach": "50g",
                "Tomato": "1 sliced",
                "Olive Oil": "1 tbsp"
            },
            "calories": 350,
            "macros": {"protein": 30, "fat": 18, "carbs": 12},
            "instructions": "Grill chicken until cooked through. Toss with spinach, tomato, and olive oil."
        },
        {
            "title": "Vegan Lentil Curry",
            "image": "https://minimalistbaker.com/wp-content/uploads/2020/12/30-Minute-Lentil-Curry-SQUARE.jpg",
            "diet": ["Vegan", "Gluten-free"],
            "ingredients": {
                "Lentils": "100g",
                "Tomato": "1 chopped",
                "Onion": "1 diced",
                "Coconut Milk": "100ml"
            },
            "calories": 420,
            "macros": {"protein": 20, "fat": 15, "carbs": 50},
            "instructions": "Cook onions, add tomatoes and lentils. Simmer with coconut milk until tender."
        },
        {
            "title": "Vegetarian Oats Bowl",
            "image": "https://www.simplyquinoa.com/wp-content/uploads/2020/03/banana-nut-oatmeal-bowl.jpg",
            "diet": ["Vegetarian"],
            "ingredients": {
                "Oats": "50g",
                "Banana": "1 sliced",
                "Milk": "100ml",
                "Almonds": "10g"
            },
            "calories": 310,
            "macros": {"protein": 10, "fat": 8, "carbs": 45},
            "instructions": "Cook oats with milk. Top with banana slices and almonds."
        }
    ]

    for r in recipes:
        insert_recipe(r)
        
# -------------------- Open AI --------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

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
LOGO_PATH = Path("./bodari_logo.png")

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
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=200)  # adjust width for aesthetic

    email = st.text_input("Email", placeholder="user@example.com")
    password = st.text_input("Password", type="password", placeholder="Enter your password")

    if st.button("Let's start"):
        conn = sqlite3.connect('bodari_users.db')
        c = conn.cursor()
        c.execute('SELECT id, password FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()

        if user:
            user_id, hashed_password = user
            if hash_password(password) == hashed_password:
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
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=200)  # same width as sign-in page

    email = st.text_input("Email", value=st.session_state.get('email', ''), placeholder="user@example.com")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")

    if st.button("Create Account"):
        if password != confirm_password:
            st.error("Passwords do not match. Please try again.")
            return

        hashed_password = hash_password(password)

        conn = sqlite3.connect('bodari_users.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hashed_password))
            conn.commit()
            user_id = c.lastrowid
            st.session_state['user_id'] = user_id
            st.session_state['page'] = 'onboarding'
            st.success("Account created successfully! Redirecting to onboarding...")
        except sqlite3.IntegrityError:
            st.error("An account with this email already exists. Please sign in.")
        finally:
            conn.close()

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

    st.image(str(LOGO_PATH), width=200)
    # Check login
    user_id = st.session_state.get('user_id')
    email = st.session_state.get('email')
    if not user_id:
        st.error("User not signed in. Redirecting to sign-in...")
        st.session_state['page'] = 'sign_in'
        return

    # Avoid duplicate onboarding
    conn = sqlite3.connect('bodari_users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM user_account WHERE user_id = ?', (user_id,))
    profile = c.fetchone()
    conn.close()

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
        conn = sqlite3.connect('bodari_users.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO user_account (user_id, name, dob, gender, height, weight, activity_level, goal, timeline, dietary_restrictions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, dob, gender, height, weight, activity_level, goal, timeline, dietary_restrictions_str))
        conn.commit()
        conn.close()

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
        st.image(str(LOGO_PATH))

    user_id = st.session_state.get('user_id')
    email = st.session_state.get('email')

    if not user_id:
        st.error("User not signed in. Redirecting to sign-in...")
        st.session_state['page'] = 'sign_in'
        return

    st.sidebar.title("Menu")
    page = st.sidebar.radio("", ["Main", "Recipes"], index=0 if st.session_state['page'] == 'main' else 1)
    if page.lower() != st.session_state['page']:
        st.session_state['page'] = page.lower()
        st.rerun()

    # Display user profile
    conn = sqlite3.connect('bodari_users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM user_account WHERE user_id = ?', (user_id,))
    profile = c.fetchone()
    conn.close()

    if not profile:
        st.warning("Profile not found. Please complete onboarding.")
        st.session_state['page'] = 'onboarding'
        return
    
    id, name, dob, gender, height, weight, activity_level, goal, timeline, dietary_restrictions = profile[0:10]
    dietary_restrictions_list = dietary_restrictions.split(',') if dietary_restrictions else []

    # Ensure dob is a date object
    if isinstance(dob, str):
        from datetime import datetime
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
            ingredients_raw = st.text_area("Ingredients and quantities (e.g. Chicken: 150g\\nRice: 100g)")
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

                # Create OpenAI prompt
                prompt = f"Estimate the total protein (g), fat (g), carbs (g), and calories for a meal named '{meal_name}' made of the following ingredients:\n"
                for ing, qty in ingredients.items():
                    prompt += f"- {ing}: {qty}\n"

                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a nutritionist assistant that estimates macronutrients."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    reply = response['choices'][0]['message']['content']
                    # Example reply: "Protein: 35g, Fat: 12g, Carbs: 40g, Calories: 480"

                    import re
                    protein = float(re.search(r"protein[:\-]?\s*(\d+)", reply, re.I).group(1))
                    fat = float(re.search(r"fat[:\-]?\s*(\d+)", reply, re.I).group(1))
                    carbs = float(re.search(r"carbs?[:\-]?\s*(\d+)", reply, re.I).group(1))
                    calories = float(re.search(r"calories[:\-]?\s*(\d+)", reply, re.I).group(1))

                    # Save to DB
                    conn = sqlite3.connect("bodari_users.db")
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO user_meals (user_id, date, meal_name, ingredients, protein, fat, carbs, calories)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id, meal_date, meal_name, json.dumps(ingredients),
                        protein, fat, carbs, calories
                    ))
                    conn.commit()
                    conn.close()

                    st.success(f"Meal '{meal_name}' saved with estimated macros!")
                    st.session_state["show_add_meal_form"] = False
                    st.rerun()

                except Exception as e:
                    st.error(f"OpenAI estimation failed: {e}")
                    
    st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)

    # Calculate daily calories and macros
    daily_calories = calories_formula(height, weight, age, gender, activity_level, goal)
    macros = macros_formula(daily_calories, goal)

    # --- Calculate Consumed Calories and Macros ---
    conn = sqlite3.connect("bodari_users.db")
    c = conn.cursor()
    c.execute("SELECT protein, fat, carbs, calories FROM user_meals WHERE user_id = ? AND date = ?", (user_id, date.today()))
    today_meals = c.fetchall()
    conn.close()

    consumed = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}
    for meal in today_meals:
        consumed['protein'] += meal[0] or 0
        consumed['fat'] += meal[1] or 0
        consumed['carbs'] += meal[2] or 0
        consumed['calories'] += meal[3] or 0

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

    selected_ingredients = st.multiselect("Select available ingredients", options=common_ingredients)

    pantry_data = []
    for ingredient in selected_ingredients:
        with st.expander(f"{ingredient} details"):
            quantity = st.number_input(f"Quantity of {ingredient}", min_value=0.0, step=10.0, format="%.2f", key=f"{ingredient}_qty")
            unit = st.selectbox(f"Unit for {ingredient}", ["grams", "kg", "ml", "liters", "cups", "pieces"], key=f"{ingredient}_unit")
            pantry_data.append((user_id, date.today(), ingredient, quantity if quantity > 0 else None, unit if quantity > 0 else "units"))

    if st.button("Save Pantry"):
        conn = sqlite3.connect('bodari_users.db')
        c = conn.cursor()
        for entry in pantry_data:
            try:
                c.execute('''
                    INSERT OR REPLACE INTO grocery_ingredients (user_id, date, ingredient, quantity, unit)
                    VALUES (?, ?, ?, ?, ?)
                ''', entry)
            except Exception as e:
                st.error(f"Error saving {entry[2]}: {e}")
        conn.commit()
        conn.close()
        st.success("✅ Pantry ingredients saved successfully!")
        st.markdown("<br>", unsafe_allow_html=True)
    
    # -------------------- Weekly Meal Plan Section --------------------
    st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
    st.markdown("### Weekly Meal Plan")
    st.markdown("Let's create a weekly meal plan tailored to your needs:")

    week_start = get_current_week_start()

    # Check pantry ingredients for today
    conn = sqlite3.connect('bodari_users.db')
    c = conn.cursor()
    c.execute('''
        SELECT ingredient, quantity, unit FROM grocery_ingredients
        WHERE user_id = ? AND date = ?
    ''', (user_id, date.today()))
    pantry_rows = c.fetchall()
    conn.close()

    pantry_ingredients_str = ""
    if pantry_rows:
        pantry_ingredients_str = "\n".join(
            [f"{ingredient} ({quantity} {unit})" for ingredient, quantity, unit in pantry_rows if quantity]
        )

    # If there's a cached meal plan and pantry is unchanged, load it
    conn = sqlite3.connect('bodari_users.db')
    c = conn.cursor()
    c.execute('''
        SELECT meal_plan FROM weekly_meal_plan
        WHERE user_id = ? AND week_start = ?
    ''', (user_id, week_start))
    row = c.fetchone()
    conn.close()

    # If meal plan already exists and pantry wasn't updated (assumes user hit Save Pantry first), load existing
    if row and not pantry_ingredients_str:
        weekly_meal_plan = row[0]
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
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a nutritionist assistant that creates healthy and balanced weekly meal plans."},
                    {"role": "user", "content": prompt}
                ]
            )
            weekly_meal_plan = response['choices'][0]['message']['content'].strip()

            # Save or update the meal plan
            conn = sqlite3.connect('bodari_users.db')
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO weekly_meal_plan (user_id, week_start, meal_plan)
                VALUES (?, ?, ?)
            ''', (user_id, week_start, weekly_meal_plan))
            conn.commit()
            conn.close()
        except openai.error.RateLimitError:
            st.warning("Rate limit reached. Waiting for 20 seconds before retrying...")
            time.sleep(20)
            return
        except Exception as e:
            st.error(f"Error in creating your weekly meal plan with OpenAI: {e}")
            return

    st.markdown(weekly_meal_plan)

    st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
    st.markdown("### Logged Meals")

    conn = sqlite3.connect("bodari_users.db")
    c = conn.cursor()
    c.execute("SELECT date, meal_name, protein, fat, carbs, calories FROM user_meals WHERE user_id = ? ORDER BY date DESC", (user_id,))
    meals = c.fetchall()
    conn.close()

    if not meals:
        st.info("You haven’t added any meals yet.")
    else:
        for meal in meals:
            m_date, name, p, f, c_, cal = meal
            st.markdown(f"**{m_date} – {name}**")
            st.markdown(f"- Protein: {p}g | Fat: {f}g | Carbs: {c_}g | Calories: {cal} kcal")


# -------------------- Recipes Page--------------------
def recipes_page():

    st.sidebar.title("Menu")
    page = st.sidebar.radio("", ["Main", "Recipes"], index=0 if st.session_state['page'] == 'main' else 1)
    if page.lower() != st.session_state['page']:
        st.session_state['page'] = page.lower()
        st.rerun()

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
                selected_ingredients = st.multiselect("Select available ingredients", all_ingredients)

        st.markdown("""<hr style='border:1px solid #ddd; margin:20px 0;'>""", unsafe_allow_html=True)

        recipes = get_all_recipes()

        def matches_filters(recipe):
            diet_ok = all(d in recipe['diet'] or d == "None" for d in selected_diets) if selected_diets else True
            ingredient_ok = any(ing in recipe['ingredients'] for ing in selected_ingredients) if selected_ingredients else True
            return diet_ok and ingredient_ok

        # Remove duplicates based on title and ingredients
        unique = {}
        for r in recipes:
            key = (r['title'].strip().lower(), json.dumps(r['ingredients'], sort_keys=True))
            if key not in unique:
                unique[key] = r
        recipes = list(unique.values())
        
        def matches_filters(recipe):
            diet_ok = all(d in recipe['diet'] or d == "None" for d in selected_diets) if selected_diets else True
            ingredient_ok = any(ing in recipe['ingredients'] for ing in selected_ingredients) if selected_ingredients else True
            return diet_ok and ingredient_ok
        
        # Show all recipes if no filters are applied, otherwise show filtered
        if not selected_diets and not selected_ingredients:
            filtered_recipes = recipes
        else:
            filtered_recipes = [r for r in recipes if matches_filters(r)]
                if not filtered_recipes:
                    st.warning("⚠️ No recipes found for selected filters.")
                    return

        for recipe in filtered_recipes:
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

# -------------------- App Initialization --------------------

create_database()

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
elif st.session_state['page'] == 'recipes':
    recipes_page()
