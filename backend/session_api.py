from fastapi import APIRouter, HTTPException
from sqlmodel import Session as SQLSession
from models import init_db, create_session, add_message, save_plan, get_latest_plan, get_messages
from nlu import parse as nlu_parse
from planner import plan_itinerary
from llm_interface import LLMWrapper
from telemetry import record_event
import os, json

router = APIRouter()
init_db()
llm = LLMWrapper()

@router.post("/session/new")
def new_session(initial_text: str = None):
    sid = create_session()
    if initial_text:
        # Ensure that the initial message, if any, is added with a dictionary meta or None
        add_message(sid, "user", initial_text, meta=None)
    return {"session_id": sid}

@router.post("/session/{session_id}/message")
def session_message(session_id: str, payload: dict):
    """
    payload: {"text": "..."}
    Returns:
      - nlu
      - plan (if produced or need_info)
      - assistant_reply (LLM-generated or clarifier)
    """
    text = payload.get("text","").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")

    # Call nlu_parse
    nlu = nlu_parse(text)
    
    # Check if nlu is a valid dictionary.
    # This prevents the previous AttributeError if nlu_parse returned a string.
    if not isinstance(nlu, dict):
        add_message(session_id, "assistant", "I'm sorry, an internal error occurred while processing your request.", meta={"type": "error"})
        raise HTTPException(status_code=500, detail="NLU parsing failed.")
    
    # store user message
    add_message(session_id, "user", text, meta=nlu)
    
    # try planning if intent is plan_trip
    if nlu.get("intent") == "plan_trip":
        plan = plan_itinerary(nlu)
        if plan.get("status") == "need_info":
            clarifier = plan.get("ask")
            add_message(session_id, "assistant", clarifier, meta={"type":"clarifier"})
            try:
                record_event(endpoint='/session/{session_id}/message', method='POST', latency_ms=0, status_code=200, note='fallback_clarifier', metadata={'session_id':session_id,'missing':plan.get('ask')})
            except Exception:
                pass
            return {"nlu": nlu, "plan": plan, "assistant": clarifier}
        else:
            # store plan
            save_plan(session_id, plan)
            try:
                record_event(endpoint='/plan/save', method='POST', latency_ms=0, status_code=200, note='plan_saved', metadata={'session_id':session_id,'n_days':plan.get('summary',{}).get('n_days')})
            except Exception:
                pass
            # ask LLM to summarize plan (augment stub)
            try:
                prompt = "You are an assistant. Summarize this travel plan briefly and give 3 quick tips for the traveler.\n\nPLAN:\n" + json.dumps(plan, ensure_ascii=False, indent=2)
                # call LLM
                reply = llm.chat(prompt)
            except Exception as e:
                reply = "[STUB] Plan generated. Add more details in further sprints."
            add_message(session_id, "assistant", reply, meta={"type":"plan_summary"})
            return {"nlu": nlu, "plan": plan, "assistant": reply}
    else:
        # Not a planning intent: ask LLM for a conversational reply
        reply = llm.chat("You are a travel assistant. Answer concisely: " + text)
        add_message(session_id, "assistant", reply)
        return {"nlu": nlu, "assistant": reply}

@router.get("/session/{session_id}/messages")
def session_history(session_id: str):
    msgs = get_messages(session_id)
    return {"messages": msgs}

@router.get("/session/{session_id}/plan")
def session_plan(session_id: str):
    p = get_latest_plan(session_id)
    if not p:
        raise HTTPException(status_code=404, detail="No plan found for session")
    return {"plan": p}
