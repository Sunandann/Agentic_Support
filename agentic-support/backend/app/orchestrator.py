"""LangGraph orchestrator: the ticket lifecycle as a directed state graph G = (V, E).

    START -> triage -> retrieval -> resolution -> escalation --continue/escalate--> finalize -> END
                          ^                            |
                          +-------------retry----------+

State S_i is checkpointed after every node (Eq. 2). If `langgraph` is not installed, an equivalent
sequential runner executes the same nodes and routing rule, so behaviour does not change.
"""
import json
import time
import traceback
from typing import Callable, TypedDict

from sqlalchemy.orm import Session

from . import services
from .agents import escalation, resolution, retrieval, triage
from .models import AgentLog, Ticket, utcnow

try:
    from langgraph.graph import END, START, StateGraph
    HAS_LANGGRAPH = True
except Exception:  # pragma: no cover - exercised only without langgraph installed
    HAS_LANGGRAPH = False


class TicketState(TypedDict, total=False):
    subject: str
    text: str
    attempt: int
    triage: dict
    evidence: list
    retrieval: dict
    resolution: dict
    escalation: dict
    decision: str
    decision_rule: str


StepHook = Callable[[str, str, dict, float, dict], None]


def _build_nodes(execute_action: Callable, on_step: StepHook) -> dict[str, Callable]:
    cache: dict[str, dict] = {}

    def exec_once(action: str, params: dict) -> dict:  # a retry loop must never run an action twice
        if action not in cache:
            cache[action] = execute_action(action, params)
        return cache[action]

    def wrap(name: str, fn: Callable[[TicketState], dict]):
        def node(state: TicketState) -> dict:
            t0 = time.perf_counter()
            out = fn(state)
            summary = out.pop("_summary", "")
            on_step(name, summary, out, (time.perf_counter() - t0) * 1000, {**state, **out})
            return out
        return node

    def esc(state: TicketState) -> dict:
        out = escalation.run(state)
        if out["escalation"]["route"] == "retry":
            out["attempt"] = state.get("attempt", 0) + 1
        return out

    def finalize(state: TicketState) -> dict:
        e = state["escalation"]
        decision = "auto-resolve" if e["route"] == "continue" else "escalate"
        return {"decision": decision, "decision_rule": e["rule"],
                "_summary": f"{decision} · {e['rule']}"}

    return {"triage": wrap("triage", triage.run),
            "retrieval": wrap("retrieval", retrieval.run),
            "resolution": wrap("resolution", lambda s: resolution.run(s, exec_once)),
            "escalation": wrap("escalation", esc),
            "finalize": wrap("finalize", finalize)}


def _route(state: TicketState) -> str:
    """Predicate rho(S) in {continue, escalate, retry}; only 'retry' loops back upstream."""
    return "retrieval" if state["escalation"]["route"] == "retry" else "finalize"


def run_pipeline(subject: str, text: str, execute_action: Callable, on_step: StepHook | None = None) -> TicketState:
    on_step = on_step or (lambda *a: None)
    nodes = _build_nodes(execute_action, on_step)
    init: TicketState = {"subject": subject, "text": text, "attempt": 0}

    if HAS_LANGGRAPH:
        g = StateGraph(TicketState)
        for name, fn in nodes.items():
            g.add_node(name, fn)
        g.add_edge(START, "triage")
        g.add_edge("triage", "retrieval")
        g.add_edge("retrieval", "resolution")
        g.add_edge("resolution", "escalation")
        g.add_conditional_edges("escalation", _route, {"retrieval": "retrieval", "finalize": "finalize"})
        g.add_edge("finalize", END)
        return g.compile().invoke(init)

    state: TicketState = dict(init)  # sequential fallback
    state.update(nodes["triage"](state))
    while True:
        state.update(nodes["retrieval"](state))
        state.update(nodes["resolution"](state))
        state.update(nodes["escalation"](state))
        if _route(state) == "finalize":
            break
    state.update(nodes["finalize"](state))
    return state


def _json_safe(obj: dict) -> dict:
    return json.loads(json.dumps(obj, default=str))


def process_ticket(db: Session, ticket: Ticket) -> Ticket:
    """Run the full pipeline for a stored ticket, logging and checkpointing every node."""
    started = time.perf_counter()
    ticket.status = "in_progress"
    db.commit()
    step = {"n": 0}

    def on_step(name: str, summary: str, output: dict, ms: float, state: dict) -> None:
        step["n"] += 1
        db.add(AgentLog(ticket_id=ticket.id, step=step["n"], agent=name, summary=summary[:500],
                        output=_json_safe(output), duration_ms=ms))
        ticket.state = _json_safe({k: v for k, v in state.items() if k != "text"})
        db.commit()

    try:
        final = run_pipeline(ticket.subject, ticket.body, lambda a, p: services.execute(db, ticket.id, a, p), on_step)
    except Exception:  # safe-fail: a broken pipeline must never auto-answer a customer
        db.rollback()
        db.add(AgentLog(ticket_id=ticket.id, step=step["n"] + 1, agent="orchestrator",
                        summary="pipeline error: escalated to human", output={"error": traceback.format_exc()[-1500:]}))
        ticket.decision, ticket.status = "escalate", "escalated"
        ticket.decision_rule = "hard_rule: pipeline error"
        ticket.processing_ms = int((time.perf_counter() - started) * 1000)
        db.commit()
        return ticket

    tri, res, esc = final["triage"], final["resolution"], final["escalation"]
    ticket.category, ticket.urgency = tri["category"], tri["urgency"]
    ticket.sentiment, ticket.priority = tri["sentiment"], tri["priority"]
    ticket.evidence, ticket.reply = final["evidence"], res["reply"]
    ticket.action, ticket.action_result = res["action"], res["action_result"]
    ticket.confidence, ticket.complexity = esc["confidence"], esc["complexity"]
    ticket.escalation_score = esc["score"]
    ticket.decision, ticket.decision_rule = final["decision"], final["decision_rule"]
    ticket.processing_ms = int((time.perf_counter() - started) * 1000)
    if final["decision"] == "auto-resolve":
        ticket.status, ticket.resolved_at = "auto_resolved", utcnow()
    else:
        ticket.status = "escalated"
    db.commit()
    return ticket
