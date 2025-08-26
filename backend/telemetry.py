
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional
from datetime import datetime
import os, uuid, json

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "telemetry.db")
DB_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})

class TelemetryEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    endpoint: str
    method: str
    latency_ms: int
    status_code: int
    note: Optional[str] = None
    metadata: Optional[str] = None

def init_telemetry_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    SQLModel.metadata.create_all(engine)

def record_event(endpoint: str, method: str, latency_ms: int, status_code: int, note: str = None, metadata: dict = None):
    with Session(engine) as s:
        e = TelemetryEvent(endpoint=endpoint, method=method, latency_ms=latency_ms, status_code=status_code,
                           note=note, metadata=json.dumps(metadata) if metadata else None)
        s.add(e)
        s.commit()
        s.refresh(e)
        return e.id

def query_metrics(limit: int = 1000):
    with Session(engine) as s:
        rows = s.exec(select(TelemetryEvent).order_by(TelemetryEvent.ts.desc()).limit(limit)).all()
        out = []
        for r in rows:
            meta = json.loads(r.metadata) if r.metadata else None
            out.append({"ts": r.ts.isoformat(), "endpoint": r.endpoint, "method": r.method, "latency_ms": r.latency_ms,
                        "status_code": r.status_code, "note": r.note, "metadata": meta})
        return out
