from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Body
import logging, os
from dotenv import load_dotenv
from llm_interface import LLMWrapper
from nlu import parse as nlu_parse

from tools import get_pois, get_city_geocode, get_weather, get_route, convert_currency, get_country_info, get_public_holidays, TOOL_MODE

from planner import plan_itinerary

load_dotenv()

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="VoyagerAI Backend", version="0.3.0")

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

@app.get("/nlu/parse")
def nlu_endpoint(text: str):
    return nlu_parse(text)

@app.post("/plan")
def plan_endpoint(payload: dict = Body(...)):
    # payload can be raw text or pre-parsed nlu
    if "text" in payload:
        nlu = nlu_parse(payload["text"])
    else:
        nlu = payload.get("nlu", {"intent":"plan_trip","entities":payload.get("entities",{})})
    plan = plan_itinerary(nlu)
    return {"nlu": nlu, "plan": plan}

@app.get("/chat")
def chat(query: str):
    # NLU first
    nlu = nlu_parse(query)
    if nlu.get("intent") == "plan_trip":
        plan = plan_itinerary(nlu)
        if plan.get("status") == "ok":
            summary = ("You are a travel assistant. A plan was generated from user constraints. "
                       "Summarize it briefly, then provide helpful tips.")
            augmented_query = summary + "\n\nPLAN JSON:\n" + str(plan) + "\n\nUser query: " + query
        else:
            augmented_query = ("Politely ask the user for the missing info and propose examples.\n"
                               f"Missing: {plan.get('ask')}\nOriginal: {query}")
        resp = llm.chat(augmented_query)
        logging.info(f"NLU: {nlu} | PLAN: {str(plan)[:300]} | Q: {query} | A: {resp[:300]}")
        return {"nlu": nlu, "plan": plan, "response": resp}
    else:
        # generic chat with NLU context
        summary = ("You are a travel assistant. Here is a structured parse of the user query: "
                   f"{nlu}. Now answer helpfully and concisely.")
        resp = llm.chat(summary + "\n\nUser: " + query)
        logging.info(f"NLU: {nlu} | Q: {query} | A: {resp[:300]}")
        return {"nlu": nlu, "response": resp}


@app.get("/tools/pois")
def api_pois(city: str, radius_m: int = 10000, limit: int = 30):
    return {"mode": TOOL_MODE, "city": city, "pois": get_pois(city, radius_m, limit)}

@app.get("/tools/weather")
def api_weather(lat: float, lon: float, start_date: str, end_date: str):
    return {"mode": TOOL_MODE, "weather": get_weather(lat, lon, start_date, end_date)}

@app.get("/tools/route")
def api_route(lat1: float, lon1: float, lat2: float, lon2: float):
    return {"mode": TOOL_MODE, "route": get_route(lat1, lon1, lat2, lon2)}

@app.get("/tools/currency")
def api_currency(amount: float, frm: str, to: str):
    return {"mode": TOOL_MODE, "result": convert_currency(amount, frm, to)}

@app.get("/tools/country")
def api_country(name: str):
    return {"mode": TOOL_MODE, "country": get_country_info(name)}

@app.get("/tools/holidays")
def api_holidays(code: str, year: int):
    return {"mode": TOOL_MODE, "holidays": get_public_holidays(code, year)}

from .session_api import router as session_router
app.include_router(session_router)
from .telemetry import init_telemetry_db, record_event, query_metrics
init_telemetry_db()


from fastapi.responses import FileResponse, JSONResponse
from .models import get_latest_plan, get_messages
from fpdf import FPDF
import os, io, tempfile

def plan_to_markdown(plan: dict) -> str:
    s = plan.get("summary",{})
    lines = []
    lines.append(f"# Itinerary — {s.get('destination','')}")
    lines.append(f"**Dates:** {s.get('start_date','')} → {s.get('end_date','')}")
    lines.append(f"**Duration:** {s.get('n_days','')} days")
    lines.append(f"**Estimated cost (INR):** ₹{s.get('est_cost_inr','')}")
    lines.append("")
    lines.append("## Day-by-day")
    for d in plan.get("days",[]):
        lines.append(f"### {d.get('date')}")
        for it in d.get("items",[]):
            lines.append(f"- {it.get('time')} — {it.get('name')} ({it.get('category')}) — {it.get('notes','')}")
        lines.append("")
    lines.append("## Notes & Assumptions")
    for a in plan.get("assumptions",[]):
        lines.append(f"- {a}")
    return "\\n".join(lines)

@app.get("/export/{session_id}")
def export_plan(session_id: str, fmt: str = "md"):
    plan = get_latest_plan(session_id)
    if not plan:
        return JSONResponse(status_code=404, content={"detail":"No plan to export"})
    md = plan_to_markdown(plan)
    if fmt == "md":
        # write to temp file and send
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".md")
        tf.write(md.encode("utf-8"))
        tf.close()
        return FileResponse(tf.name, media_type="text/markdown", filename=f"itinerary_{session_id}.md")
    # generate simple PDF (fpdf)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.multi_cell(0, 8, md)
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tf.name)
    return FileResponse(tf.name, media_type="application/pdf", filename=f"itinerary_{session_id}.pdf")


# --- Telemetry middleware (measures latency & status) ---
from fastapi import Request
import time
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start = time.time()
    try:
        resp = await call_next(request)
        status = resp.status_code
    except Exception as e:
        status = 500
        raise
    finally:
        latency_ms = int((time.time() - start) * 1000)
        try:
            record_event(endpoint=str(request.url.path), method=request.method, latency_ms=latency_ms, status_code=status)
        except Exception:
            pass
    return resp


@app.get("/telemetry/metrics")
def get_telemetry(limit: int = 500):
    return {"metrics": query_metrics(limit)}
