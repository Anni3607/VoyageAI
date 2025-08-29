import logging
import os
import uvicorn
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware

# Use a non-relative import for your internal modules.
# This assumes that 'llm_interface', 'tools', and 'planner'
# are at the same level as 'main.py' in the 'backend' directory.
from llm_interface import LLMWrapper
from tools import get_pois, get_city_geocode, get_weather, get_route, convert_currency, get_country_info, get_public_holidays, TOOL_MODE
from planner import plan_itinerary

# Load environment variables.
from dotenv import load_dotenv
load_dotenv()

# Create a logs directory if it doesn't exist.
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Initialize the FastAPI app.
app = FastAPI(title="VoyagerAI Backend")

# Add CORS middleware to allow cross-origin requests from your frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize the LLMWrapper.
llm_wrapper = LLMWrapper()

# A simple root endpoint to check if the backend is running.
@app.get("/")
def read_root():
    """
    Returns a status message and the current LLM backend.
    """
    return {"service": "voyagerai-backend", "status": "ok", "llm_backend": llm_wrapper.backend}


# A temporary endpoint to fix the JSON decode error on the frontend.
@app.post("/session/new")
def new_session():
    """
    A temporary endpoint to simulate a new session.
    This is to fix the JSONDecodeError on the frontend.
    """
    return {"session_id": "dummy-session-id", "message": "New session created."}


# This is your main chat endpoint.
@app.post("/session/{session_id}")
async def chat_with_session(session_id: str, prompt: str = Body(..., embed=True)):
    """
    Handles chat interactions with a specific session.
    """
    # Use the LLM wrapper to get a response.
    # We will expand on the logic here later.
    response = llm_wrapper.chat(prompt)
    return {"session_id": session_id, "message": response}


# This is the main entry point for the application.
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
