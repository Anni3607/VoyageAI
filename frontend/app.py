
import streamlit as st
import requests
import os

st.set_page_config(page_title="VoyagerAI", page_icon="🌍")
st.title("🌍 VoyagerAI — Smart Travel Planner (Skeleton)")

BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL","http://127.0.0.1:8000"))

query = st.text_input("Ask a travel question (skeleton demo):", "Plan a 3-day Goa trip under ₹20,000 from Mumbai in October")
if st.button("Send"):
    try:
        r = requests.get(f"{BACKEND_URL}/chat", params={"query": query}, timeout=60)
        st.write("**Bot:**", r.json().get("response","(no response)"))
    except Exception as e:
        st.error(f"Backend error: {e}")

st.caption("Backend URL: " + BACKEND_URL)
