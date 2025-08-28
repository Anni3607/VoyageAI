
import streamlit as st
import requests, os
from datetime import datetime

st.set_page_config(page_title="VoyagerAI — Chat Planner", layout="centered")
st.title("🌍 VoyagerAI — Smart Travel Planner (Chat)")

BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL","https://voyageai-9.onrender.com"))

# session management
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

def new_session(initial_text=None):
    r = requests.post(f"{BACKEND_URL}/session/new", json={"initial_text": initial_text} if initial_text else {})
    sid = r.json().get("session_id")
    st.session_state.session_id = sid
    st.session_state.messages = []
    return sid

def send_message(text):
    sid = st.session_state.session_id or new_session()
    payload = {"text": text}
    r = requests.post(f"{BACKEND_URL}/session/{sid}/message", json=payload, timeout=60)
    return r.json()

# UI
placeholder = st.empty()
with placeholder.container():
    col1, col2 = st.columns([3,1])
    with col1:
        user_input = st.text_input("You:", key="input_text", placeholder="E.g., Plan a 3-day Goa trip from Mumbai under ₹20000 in October")
    with col2:
        if st.button("New Chat"):
            new_session()
            st.experimental_rerun()

    if st.button("Send"):
        text = st.session_state.get("input_text","").strip()
        if text:
            resp = send_message(text)
            # append user
            st.session_state.messages.append({"role":"user","text":text})
            # assistant
            assistant = resp.get("assistant","(no reply)")
            st.session_state.messages.append({"role":"assistant","text":assistant})
            # if plan returned, show plan summary
            plan = resp.get("plan")
            if plan and plan.get("status")=="ok":
                st.session_state.latest_plan = plan

    # render messages
    for m in st.session_state.messages:
        if m["role"]=="user":
            st.markdown(f"**You:** {m['text']}")
        else:
            st.markdown(f"**VoyagerAI:** {m['text']}")

# If a plan exists (either from state or fetch)
plan = st.session_state.get("latest_plan", None)
if not plan and st.session_state.session_id:
    try:
        r = requests.get(f"{BACKEND_URL}/session/{st.session_state.session_id}/plan", timeout=3)
        if r.status_code == 200:
            plan = r.json().get("plan")
            st.session_state.latest_plan = plan
    except Exception:
        pass

if plan:
    st.markdown("### Generated Itinerary")
    s = plan.get("summary",{})
    st.markdown(f"**{s.get('destination','')}** | {s.get('start_date','')} → {s.get('end_date','')} | **{s.get('n_days','')} days**")
    st.markdown(f"**Est. Cost:** ₹{s.get('est_cost_inr','')} — {s.get('notes','')}")
    for d in plan.get("days",[]):
        st.markdown(f"**{d.get('date')}**")
        for it in d.get("items",[]):
            st.write(f"- `{it.get('time')}` — **{it.get('name')}** ({it.get('category')})  \n  {it.get('notes','')}")
    st.markdown("#### Export")
    colx, coly = st.columns(2)
    with colx:
        if st.button("Download Markdown"):
            r = requests.get(f"{BACKEND_URL}/export/{st.session_state.session_id}?fmt=md", stream=True)
            if r.status_code == 200:
                st.download_button("Download .md", r.content, file_name=f"itinerary_{st.session_state.session_id}.md", mime="text/markdown")
            else:
                st.error("Export failed.")
    with coly:
        if st.button("Download PDF"):
            r = requests.get(f"{BACKEND_URL}/export/{st.session_state.session_id}?fmt=pdf", stream=True)
            if r.status_code == 200:
                st.download_button("Download .pdf", r.content, file_name=f"itinerary_{st.session_state.session_id}.pdf", mime="application/pdf")
            else:
                st.error("Export failed.")
