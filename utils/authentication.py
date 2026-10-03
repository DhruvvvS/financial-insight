""" 
    Authentication
    A minimal authentication gate for FinSight, SQLite for storage, passlib/bcrypt for password
    hashing, st.session_state standing in for "the session" 
    
    No JWT here on purpose: there's no separate client sending an
    Authorization header to a FastAPI backend, so a Bearer token has
    nothing to attach to.
"""

# import for storage and hashing.
import sqlite3
import bcrypt

# import for session state and file path.
from pathlib import Path
import streamlit as st

# import for locking out users after too many failed attempts.
import time

Db_Path = Path(__file__).resolve().parent.parent / "users.db"
# .resolve() to convert to full absolute path,
# .parent.parent to go up two levels to the root of the project

Max_Login_Attempts = 5
Lockout_Duration = 60  # in seconds

# Initialize the database and create the users table if it doesn't exist.
def init_db():
    # conn means connection to the database, and we use it to execute SQL commands.
    conn = sqlite3.connect(Db_Path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Register a new user with a hashed password.
def register_user(username, password):
    username = username.strip()
    if not username or not password:
        return False, "Username and password cannot be empty."
    if len(password) < 7:
        return False, "Password must be at least 7 characters long."

    # Hash the password using bcrypt.

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    """
    password.encode('utf-8') converts the password string to bytes, which is required by bcrypt.
    bcrypt.gensalt() generates a random salt for hashing.
    .decode('utf-8') converts the hashed password back to a string for storage in the database.
    """

    # Connect to the SQLite database and insert the new user.
    conn = sqlite3.connect(Db_Path)

    try:
        conn.execute(
            'INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password)
            )
        conn.commit()
        return True, "User registered successfully."
    
    except sqlite3.IntegrityError:
        # This error occurs if the username already exists in the database.
        return False, "Username already exists."
    
    finally:
        conn.close()

# Verify the user's credentials.
def verify_user(username, password):
    
    conn = sqlite3.connect(Db_Path)
    conn.execute(
        'SELECT password FROM users WHERE username = ?', (username,)
        )
    result = conn.fetchone()
    conn.close()

    # Returns True if the username exists and the password matches, False otherwise.
    if result:
        stored_password = result[0]
        # Check if the provided password matches the stored hashed password.
        return bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
    
    return False

"""
We will call this login gate function at the start of app.py to check if the user is authenticated.
If the user is not authenticated, we will show the login form and handle the login process.
"""

def login_gate():
    init_db()

    if st.session_state.get("authenticated"):
        return  # already logged in this session — let app.py continue
 
    # rate limiting: track failed attempts in this session
    attempts = st.session_state.get("login_attempts", 0)
    locked_until = st.session_state.get("locked_until", 0)
 
    st.title("FinSight — Sign In")

    # Check if the user is currently locked out due to too many failed attempts. 
    if time.time() < locked_until:
        wait = int(locked_until - time.time()) # how many seconds left to wait
        st.error(f"Too many failed attempts. Try again in {wait} seconds.")
        st.stop()

    # Create tabs for login and registration forms.
    tab_login, tab_register = st.tabs(["Login", "Create Account"])

    # Login Form
    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In")
 
        if submitted:
            
            if verify_user(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["login_attempts"] = 0
                st.rerun() # rerun the app to reflect the authenticated state
            
            else:
                attempts += 1
                st.session_state["login_attempts"] = attempts
                
                if attempts >= Max_Login_Attempts:
                    st.session_state["locked_until"] = time.time() + Lockout_Duration
                    st.error(f"Too many failed attempts. Locked for {Lockout_Duration} seconds.")
                else:
                    # specifically — don't help an attacker enumerate accounts.
                    st.error("Invalid username or password.")

    # Registration Form
    with tab_register:
        
        with st.form("register_form"):
            new_username = st.text_input("Choose a username")
            new_password = st.text_input("Choose a password (min 8 characters)", type="password")
            reg_submitted = st.form_submit_button("Create Account")
 
        if reg_submitted:
            success, message = register_user(new_username, new_password)
            if success:
                st.success(message)
            else:
                st.error(message)
 
    st.stop() # Stop the app here to prevent further execution until the user is authenticated.