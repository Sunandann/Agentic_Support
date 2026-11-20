"""Persistence layer: tickets, per-agent audit log, knowledge base, executed actions."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(32), default="web")
    customer_id: Mapped[str] = mapped_column(String(64), default="anonymous")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # open -> in_progress -> auto_resolved | escalated -> resolved
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)

    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    urgency: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[float | None] = mapped_column(Float, nullable=True)

    reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)

    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    complexity: Mapped[float | None] = mapped_column(Float, nullable=True)
    escalation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision_rule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processing_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    human_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalation_justified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    state: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # last orchestrator checkpoint

    logs: Mapped[list["AgentLog"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="AgentLog.id")

    def to_dict(self, detail: bool = False) -> dict:
        d = {
            "id": self.id, "subject": self.subject, "body": self.body, "channel": self.channel,
            "customer_id": self.customer_id, "status": self.status, "category": self.category,
            "urgency": self.urgency, "sentiment": self.sentiment, "priority": self.priority,
            "decision": self.decision, "confidence": self.confidence, "complexity": self.complexity,
            "escalation_score": self.escalation_score, "decision_rule": self.decision_rule,
            "action": self.action, "processing_ms": self.processing_ms,
            "created_at": iso(self.created_at), "resolved_at": iso(self.resolved_at),
            "escalation_justified": self.escalation_justified,
        }
        if detail:
            d.update({
                "reply": self.reply, "action_result": self.action_result, "evidence": self.evidence,
                "human_resolution": self.human_resolution,
                "logs": [l.to_dict() for l in self.logs],
            })
        return d


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    step: Mapped[int] = mapped_column(Integer)
    agent: Mapped[str] = mapped_column(String(32), index=True)
    summary: Mapped[str] = mapped_column(String(500), default="")
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="logs")

    def to_dict(self) -> dict:
        return {"id": self.id, "step": self.step, "agent": self.agent, "summary": self.summary,
                "output": self.output, "duration_ms": round(self.duration_ms, 2),
                "created_at": iso(self.created_at)}


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), default="general")
    source: Mapped[str] = mapped_column(String(24), default="faq")  # faq | doc | resolution
    ticket_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "content": self.content,
                "category": self.category, "source": self.source, "ticket_id": self.ticket_id,
                "created_at": iso(self.created_at)}


class ActionRecord(Base):
    """Backend side-effects executed by the Resolution Agent (the bounded A_routine set)."""
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
