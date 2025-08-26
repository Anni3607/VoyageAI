"""
voyagerai/backend/telegram_bot.py

Simple Telegram bot that forwards user messages to the VoyagerAI backend (/session/new and /session/{id}/message)
Modes:
 - Polling (default): run locally or on a VM/always-on service (small demo only)
 - Webhook: set TELEGRAM_WEBHOOK_URL and use web server to accept updates (for production)
"""
import os, requests, time, threading, logging
from typing import Optional

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
POLL_INTERVAL = float(os.getenv("TELEGRAM_POLL_INTERVAL", "1.5"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voyagerai.telegram")

def ensure_session(chat_id: str) -> str:
    """
    Create a VoyagerAI session per chat_id (simple: map chat_id -> session through backend session creation).
    For demo we create a new session per chat_id and store mapping in memory (lost on restart).
    """
    # In production you'd persist mapping in DB; here we call /session/new and keep mapping in local file
    mapping_file = os.path.join(os.path.dirname(__file__), "..", "data", "tg_session_map.json")
    try:
        m = {}
        if os.path.exists(mapping_file):
            import json
            m = json.load(open(mapping_file, "r", encoding="utf-8"))
        if chat_id in m:
            return m[chat_id]
        # create session
        r = requests.post(f"{BACKEND_URL}/session/new", json={})
        r.raise_for_status()
        sid = r.json().get("session_id")
        m[chat_id] = sid
        open(mapping_file, "w", encoding="utf-8").write(json.dumps(m))
        return sid
    except Exception as e:
        logger.exception("Failed to ensure session")
        raise

def send_to_backend(chat_id: str, text: str):
    sid = ensure_session(str(chat_id))
    payload = {"text": text}
    r = requests.post(f"{BACKEND_URL}/session/{sid}/message", json=payload, timeout=20)
    r.raise_for_status()
    j = r.json()
    # prefer assistant field
    assistant = j.get("assistant") or j.get("response") or "(no reply)"
    return assistant, j

# --- Polling implementation using python-telegram-bot optional dependency ---
def start_polling():
    try:
        from telegram import Update, Bot
        from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
    except Exception as e:
        logger.error("Missing python-telegram-bot. Install with: pip install python-telegram-bot==20.5")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Hi! I'm VoyagerAI. Tell me where you'd like to go and your constraints (budget, dates, origin).")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        txt = update.message.text or ""
        chat_id = update.message.chat_id
        await update.message.reply_text("Got it — working on that...")
        try:
            assistant, raw = send_to_backend(chat_id, txt)
            await update.message.reply_text(str(assistant))
        except Exception as e:
            logger.exception("Bot backend failure")
            await update.message.reply_text("Sorry, something went wrong contacting the planner.")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Starting Telegram polling...")
    app.run_polling(poll_interval=POLL_INTERVAL)

# Webhook mode (optional)
def webhook_handler(update_json: dict):
    """
    If you prefer to receive updates via webhook, call this function with Telegram update JSON.
    Returns dict with reply text and raw backend response.
    """
    try:
        msg = update_json.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id"))
        text = msg.get("text","")
        assistant, raw = send_to_backend(chat_id, text)
        return {"reply": assistant, "raw": raw}
    except Exception as e:
        logger.exception("webhook error")
        return {"error": str(e)}

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN set in environment. Exiting.")
    else:
        start_polling()
