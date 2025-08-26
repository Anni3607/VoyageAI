
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging, os
from dotenv import load_dotenv
from .llm_interface import LLMWrapper

load_dotenv()

# Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="VoyagerAI Backend", version="0.1.0")

# CORS
origins = [o.strip() for o in os.getenv("CORS_ORIGINS","*").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = LLMWrapper()

@app.get("/")
def root():
    return {"service":"voyagerai-backend","status":"ok","llm_backend": os.getenv("LLM_BACKEND","stub")}

@app.get("/chat")
def chat(query: str):
    resp = llm.chat(query)
    logging.info(f"Q: {query} | A: {resp[:300]}")
    return {"response": resp}
