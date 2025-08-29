import os
import requests
import streamlit as st

# Configure the page title and layout
st.set_page_config(page_title="VoyagerAI - Smart Travel Planner", layout="wide")

# Get the backend URL from environment variables directly.
# This is a robust way to handle environment variables on platforms like Render.
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Session state initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def new_session():
    """Starts a new chat session by clearing history and getting a new session ID from backend."""
    st.session_state.chat_history = []
    try:
        # Use the correct endpoint for a new session
        r = requests.post(f"{BACKEND_URL}/session/new")
        r.raise_for_status()
        st.session_state.session_id = r.json().get("session_id")
        # In Streamlit, st.experimental_rerun() is used to force a refresh.
        # This can be replaced with st.rerun() in newer versions of Streamlit.
        st.experimental_rerun()
    except requests.exceptions.RequestException as e:
        st.error(f"Error creating new session: {e}")
        st.session_state.session_id = None

def send_message(text):
    """Sends a message to the backend and appends the response to the chat history."""
    if st.session_state.session_id:
        try:
            r = requests.post(
                f"{BACKEND_URL}/session/{st.session_state.session_id}",
                json={"prompt": text}
            )
            r.raise_for_status()
            response_data = r.json()
            st.session_state.chat_history.append({"role": "user", "content": text})
            st.session_state.chat_history.append({"role": "VoyagerAI", "content": response_data.get("message")})
            st.experimental_rerun()
        except requests.exceptions.RequestException as e:
            st.error(f"Error sending message: {e}")
            st.session_state.chat_history.append({"role": "user", "content": text})
            st.session_state.chat_history.append({"role": "VoyagerAI", "content": f"Error: {e}"})

# Main app UI
st.title("VoyagerAI — Smart Travel Planner :)")

# Layout for input and buttons
input_col, new_chat_col = st.columns([4, 1])

with input_col:
    user_input = st.text_input("You:", placeholder="plan a 3 day tour to Goa from mumbai in october", key="user_input")

with new_chat_col:
    st.write("") # Add some space
    if st.button("New Chat"):
        new_session()

if st.button("Send"):
    if user_input:
        send_message(user_input)

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Automatically start a new session on page load if one doesn't exist.
if st.session_state.session_id is None:
    st.info("Creating a new chat session...")
    new_session()
