"""FastAPI backend: ticket ingestion, status API, dashboard stats, knowledge base, feedback loop."""
import json
from collections import Counter
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import knowledge
from .config import DATA_DIR, settings
from .database import Base, SessionLocal, engine, get_db
from .llm import llm
from .models import ActionRecord, AgentLog, KnowledgeDoc, Ticket, iso, utcnow
from .orchestrator import HAS_LANGGRAPH, process_ticket


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        knowledge.seed_knowledge(db)
    yield


app = FastAPI(title="Agentic AI Customer Support", version="1.0.0", lifespan=lifespan,
              description="Orchestrator-Worker multi-agent ticket resolution with grounded retrieval "
                          "and confidence-based escalation.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


class TicketIn(BaseModel):
    subject: str = Field("", max_length=255)
    body: str = Field(..., min_length=3, max_length=8000)
    channel: str = Field("web", max_length=32)
    customer_id: str = Field("anonymous", max_length=64)


class ResolveIn(BaseModel):
    resolution: str = Field(..., min_length=3)
    escalation_justified: bool = True
    add_to_kb: bool = True


class KBIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=3)
    category: str = "general"
    source: str = "faq"


@app.get("/api/health")
def health():
    return {"status": "ok", "langgraph": HAS_LANGGRAPH, "llm": llm.enabled,
            "mode": "llm" if llm.enabled else "offline-template", "kb_size": len(knowledge.store),
            "config": {"tau": settings.tau, "top_k": settings.top_k}}


@app.post("/api/tickets", status_code=201)
def create_ticket(payload: TicketIn, db: Session = Depends(get_db)):
    ticket = Ticket(subject=payload.subject.strip(), body=payload.body.strip(),
                    channel=payload.channel, customer_id=payload.customer_id)
    db.add(ticket)
    db.commit()
    process_ticket(db, ticket)
    db.refresh(ticket)
    return ticket.to_dict(detail=True)


@app.get("/api/tickets")
def list_tickets(status: str | None = None, category: str | None = None, limit: int = Query(100, le=500),
                 db: Session = Depends(get_db)):
    q = db.query(Ticket)
    if status:
        q = q.filter(Ticket.status == status)
    if category:
        q = q.filter(Ticket.category == category)
    rows = q.order_by(Ticket.id.desc()).limit(limit).all()
    return [t.to_dict() for t in rows]


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    return t.to_dict(detail=True)


@app.post("/api/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: int, payload: ResolveIn, db: Session = Depends(get_db)):
    """A human representative closes an escalated ticket; the answer can enrich the knowledge base."""
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    if t.status != "escalated":
        raise HTTPException(409, "Only escalated tickets can be resolved by a human")
    t.human_resolution, t.escalation_justified = payload.resolution, payload.escalation_justified
    t.status, t.resolved_at = "resolved", utcnow()
    db.commit()
    if payload.add_to_kb:
        knowledge.add_doc(db, t.subject or t.body[:80], payload.resolution, t.category or "general",
                          "resolution", t.id)
    return t.to_dict(detail=True)


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    tickets = db.query(Ticket).all()
    total = len(tickets)
    by_status = Counter(t.status for t in tickets)
    processed = [t for t in tickets if t.decision]
    auto = [t for t in processed if t.decision == "auto-resolve"]
    esc = [t for t in processed if t.decision == "escalate"]
    done = [t for t in tickets if t.resolved_at]
    handling = [(t.resolved_at - t.created_at).total_seconds() for t in done]
    auto_h = [(t.resolved_at - t.created_at).total_seconds() for t in done if t.decision == "auto-resolve"]
    human_h = [(t.resolved_at - t.created_at).total_seconds() for t in done if t.decision == "escalate"]
    reviewed = [t for t in esc if t.escalation_justified is not None]
    justified = [t for t in reviewed if t.escalation_justified]

    def avg(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    agent_rows = db.query(AgentLog.agent, func.count(AgentLog.id), func.avg(AgentLog.duration_ms)).group_by(AgentLog.agent).all()
    today = utcnow().date()
    trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day = [t for t in tickets if t.created_at.date() == d]
        trend.append({"date": d.isoformat(), "total": len(day),
                      "auto": sum(1 for t in day if t.decision == "auto-resolve"),
                      "escalated": sum(1 for t in day if t.decision == "escalate")})
    return {
        "total": total,
        "by_status": {k: by_status.get(k, 0) for k in ("open", "in_progress", "auto_resolved", "escalated", "resolved")},
        "first_contact_resolution_rate": round(len(auto) / len(processed), 4) if processed else None,
        "escalation_rate": round(len(esc) / len(processed), 4) if processed else None,
        "escalation_precision": round(len(justified) / len(reviewed), 4) if reviewed else None,
        "escalations_reviewed": len(reviewed),
        "avg_handling_seconds": avg(handling), "avg_handling_auto_seconds": avg(auto_h),
        "avg_handling_human_seconds": avg(human_h),
        "avg_processing_ms": avg([t.processing_ms for t in processed if t.processing_ms is not None]),
        "avg_confidence": avg([t.confidence for t in processed if t.confidence is not None]),
        "categories": dict(Counter(t.category for t in tickets if t.category)),
        "agents": [{"agent": a, "runs": n, "avg_ms": round(float(ms or 0), 2)} for a, n, ms in agent_rows],
        "actions_executed": db.query(ActionRecord).count(),
        "kb_size": db.query(KnowledgeDoc).count(),
        "trend": trend,
    }


@app.get("/api/kb")
def list_kb(db: Session = Depends(get_db)):
    return [d.to_dict() for d in db.query(KnowledgeDoc).order_by(KnowledgeDoc.id.desc()).all()]


@app.post("/api/kb", status_code=201)
def add_kb(payload: KBIn, db: Session = Depends(get_db)):
    return knowledge.add_doc(db, payload.title, payload.content, payload.category, payload.source).to_dict()


@app.post("/api/feedback/run")
def feedback_loop(db: Session = Depends(get_db)):
    """Periodic feedback loop: fold resolved tickets that are not yet in the KB back into V."""
    known = {d.ticket_id for d in db.query(KnowledgeDoc).filter(KnowledgeDoc.ticket_id.isnot(None))}
    added = 0
    for t in db.query(Ticket).filter(Ticket.status.in_(["resolved", "auto_resolved"])).all():
        if t.id in known:
            continue
        content = t.human_resolution or t.reply
        if content:
            db.add(KnowledgeDoc(title=(t.subject or t.body[:80]), content=content,
                                category=t.category or "general", source="resolution", ticket_id=t.id))
            added += 1
    db.commit()
    knowledge.load_store(db)
    return {"added": added, "kb_size": len(knowledge.store)}


@app.post("/api/demo/seed")
def seed_demo(db: Session = Depends(get_db)):
    """Load a handful of realistic tickets so the dashboard has something to show."""
    items = json.loads((DATA_DIR / "demo_tickets.json").read_text(encoding="utf-8"))
    out = []
    for item in items:
        t = Ticket(subject=item["subject"], body=item["body"], channel=item.get("channel", "email"),
                   customer_id=item.get("customer_id", "demo"))
        db.add(t)
        db.commit()
        process_ticket(db, t)
        out.append(t.id)
    return {"created": out}
