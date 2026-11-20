"""Escalation Agent: Conf(t), Cplx(t), score X (Eq. 5) and routing decision (Eq. 6)."""
from ..config import settings
from ..knowledge import store
from .base import AgentSpec, clip

SPEC = AgentSpec(
    "escalation", "Escalation Gatekeeper",
    "Decide whether a drafted resolution is safe to send or must go to a human with the full trail.",
    "A cautious team lead who would rather hand over one ticket too many than send one wrong answer.")


def _consistency(state: dict) -> float:
    """Self-consistency of the draft. With an LLM: agreement between sampled drafts.
    Offline: agreement between the retrieved passages the draft is built from."""
    samples = state["resolution"].get("samples")
    if samples and len(samples) > 1:
        pairs = [store.text_similarity(samples[i], samples[j])
                 for i in range(len(samples)) for j in range(i + 1, len(samples))]
        return clip((sum(pairs) / len(pairs)) / 0.6)
    return clip(state["retrieval"]["agreement"] / 0.25)


def run(state: dict) -> dict:
    tri, ret, res = state["triage"], state["retrieval"], state["resolution"]
    strength = clip(ret["top_score"] / settings.sim_ref)
    conf = clip(0.7 * strength + 0.3 * _consistency(state))
    out_of_scope = bool(res["out_of_scope"])
    cplx = clip(0.5 * ret["disagreement"] + 0.25 * tri["urgency"] + 0.25 * (1.0 if out_of_scope else 0.0))
    x = settings.lam1 * (1 - conf) + settings.lam2 * cplx + settings.lam3 * tri["urgency"]  # Eq. (5)

    attempt = state.get("attempt", 0)
    if out_of_scope:
        route, rule = "escalate", "hard_rule: needs a human (outside routine actions or explicitly requested)"
    elif not state["evidence"]:
        route, rule = "escalate", "hard_rule: no supporting evidence retrieved"
    elif x > settings.tau and attempt < settings.max_retries and strength < 0.6:
        route, rule = "retry", f"X={x:.3f} > tau={settings.tau} with weak retrieval: widening search"
    elif x > settings.tau:
        route, rule = "escalate", f"X={x:.3f} > tau={settings.tau}"
    else:
        route, rule = "continue", f"X={x:.3f} <= tau={settings.tau}"

    return {"escalation": {"confidence": round(conf, 3), "complexity": round(cplx, 3),
                           "score": round(x, 3), "tau": settings.tau, "route": route, "rule": rule,
                           "retrieval_strength": round(strength, 3)},
            "_summary": f"Conf {conf:.2f} · Cplx {cplx:.2f} · X {x:.2f} vs tau {settings.tau} → {route}"}
