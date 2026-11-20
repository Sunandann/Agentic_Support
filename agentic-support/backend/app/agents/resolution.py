"""Resolution Agent: drafts r_i from evidence E_i and may run one routine action a_i in A_routine."""
import re

from ..llm import llm
from ..services import ROUTINE_ACTIONS
from .base import AgentSpec

SPEC = AgentSpec(
    "resolution", "Customer Resolution Specialist",
    "Write an accurate, friendly reply grounded only in retrieved evidence and run safe routine actions.",
    "A senior support agent who never promises anything the knowledge base cannot back up.")

ACTION_PATTERNS = {
    "password_reset": r"(reset|forgot|forgotten|change).{0,20}password|(can'?t|cannot|unable to).{0,15}(log ?in|sign in)|locked out",
    "refund_initiation": r"refund|money back|charged twice|double charged|duplicate charge",
    "account_update": r"(update|change|edit|correct).{0,15}(my )?(e-?mail|phone|address|name)",
}
# Anything here is never executed automatically: the Escalation Agent hands it to a human.
RESTRICTED = (r"delete (my|the) account|close (my|the) account|charge ?back|dispute|lawyer|attorney|legal action|"
              r"\bsue\b|lawsuit|compensat|data breach|gdpr|unauthori[sz]ed (charge|transaction|access|purchase|payment|activity|login)|"
              r"fraud|hacked|stolen|police|regulator|consumer court|cancel (my )?contract|termination fee|"
              r"call me|\bmanager\b|supervisor|speak (to|with) (a |the )?(person|someone)")
ORDER_RE = re.compile(r"(?:order\s*(?:no\.?|number|#)?\s*[:#]?\s*)?\b(ORD-?\d{3,}|#\d{4,})\b", re.I)


def detect_action(text: str) -> tuple[str | None, bool, dict]:
    t = text.lower()
    restricted = bool(re.search(RESTRICTED, t))
    params: dict = {}
    m = ORDER_RE.search(text)
    if m:
        params["order_id"] = m.group(1).upper()
    for action, pat in ACTION_PATTERNS.items():
        if re.search(pat, t) and action in ROUTINE_ACTIONS:
            return action, restricted, params
    return None, restricted, params


def _template_reply(state: dict, action: str | None, action_result: dict | None) -> str:
    ev = state.get("evidence") or []
    lines = ["Hello,", "", "Thanks for getting in touch."]
    if ev:
        lines.append(ev[0]["content"])
        extra = next((e for e in ev[1:] if e["category"] == ev[0]["category"]
                      and e["score"] >= 0.6 * ev[0]["score"]), None)
        if extra:
            lines.append(extra["content"])
    else:
        lines.append("We are looking into this and a team member will follow up shortly.")
    if action and action_result:
        if action_result.get("executed"):
            lines.append(f"We have already taken care of the next step: {action_result['detail']} "
                         f"(reference {action_result['reference']}).")
        elif action == "refund_initiation":
            lines.append("To start the refund review, please reply with your order number.")
    lines += ["", "If this does not solve it, just reply and we will keep helping.", "Support Team"]
    return "\n".join(lines)


def _llm_reply(state: dict, action_note: str, n: int) -> list[str] | None:
    ctx = "\n\n".join(f"[{i + 1}] {e['title']}: {e['content']}" for i, e in enumerate(state["evidence"]))
    system = ("You are a customer support agent. Answer ONLY using the numbered evidence. If the evidence "
              "does not answer the question, say a specialist will follow up. Be concise and polite.")
    prompt = (f"Ticket subject: {state['subject']}\nTicket: {state['text']}\n\nEvidence:\n{ctx}\n\n"
              f"Action status: {action_note}\n\nWrite the reply.")
    return llm.complete(system, prompt, temperature=0.7 if n > 1 else 0.2, n=n)


def run(state: dict, execute_action) -> dict:
    """`execute_action(action, params)` is injected by the orchestrator so tests can stub services."""
    action, restricted, params = detect_action(f"{state['subject']} {state['text']}")
    action_result = None
    if action and not restricted and state["evidence"]:
        action_result = execute_action(action, params)

    samples = None
    if llm.enabled and state["evidence"]:
        note = action_result["detail"] if action_result and action_result.get("executed") else "none"
        samples = _llm_reply(state, note, n=3)
    reply = samples[0] if samples else _template_reply(state, action, action_result)
    return {"resolution": {"reply": reply, "action": action, "action_params": params,
                           "action_result": action_result, "out_of_scope": restricted,
                           "samples": samples, "mode": "llm" if samples else "template"},
            "_summary": f"{'LLM' if samples else 'template'} reply drafted"
                        + (f" · action {action}" if action else "")
                        + (" · restricted request detected" if restricted else "")}
