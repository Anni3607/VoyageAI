
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional
from datetime import datetime
import uuid, os, json

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sessions.db")
DB_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})

class ChatSession(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    role: str  # "user" or "assistant" or "system"
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    meta: Optional[str] = None  # JSON string for extra data (NLU, plan summary)

class Itinerary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    plan_json: str = ""  # serialized plan

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    SQLModel.metadata.create_all(engine)

def create_session() -> str:
    sid = str(uuid.uuid4())
    s = ChatSession(id=sid)
    with Session(engine) as session:
        session.add(s)
        session.commit()
    return sid

def add_message(session_id: str, role: str, text: str, meta: dict = None):
    with Session(engine) as db:
        m = Message(session_id=session_id, role=role, text=text, meta=json.dumps(meta) if meta else None)
        db.add(m)
        db.commit()
        db.refresh(m)
        # update last_active on session
        q = db.exec(select(ChatSession).where(ChatSession.id == session_id)).one()
        q.last_active = datetime.utcnow()
        db.add(q)
        db.commit()
    return m.id

def save_plan(session_id: str, plan: dict):
    with Session(engine) as db:
        it = Itinerary(session_id=session_id, plan_json=json.dumps(plan, ensure_ascii=False))
        db.add(it)
        db.commit()
        db.refresh(it)
    return it.id

def get_latest_plan(session_id: str):
    with Session(engine) as db:
        res = db.exec(select(Itinerary).where(Itinerary.session_id == session_id).order_by(Itinerary.created_at.desc())).first()
        if res:
            return json.loads(res.plan_json)
    return None

def get_messages(session_id: str):
    with Session(engine) as db:
        rows = db.exec(select(Message).where(Message.session_id == session_id).order_by(Message.created_at)).all()
        out = []
        for r in rows:
            meta = json.loads(r.meta) if r.meta else None
            out.append({"role": r.role, "text": r.text, "created_at": r.created_at.isoformat(), "meta": meta})
        return out
