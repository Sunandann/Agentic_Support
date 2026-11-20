"""Retrieval Agent: grounds the reply in top-k organisational evidence E_i (Eq. 4)."""
from collections import Counter

from ..config import settings
from ..knowledge import store
from .base import AgentSpec

SPEC = AgentSpec(
    "retrieval", "Knowledge Retrieval Specialist",
    "Find the most relevant FAQ, documentation and past-resolution passages for the ticket.",
    "A meticulous librarian who only hands over sources that actually answer the question.")


def run(state: dict) -> dict:
    attempt = state.get("attempt", 0)
    category = state["triage"]["category"]
    # First pass: ticket text + triage category. Retry pass: wider net (more passages, subject repeated).
    query = f"{state['subject']} {state['text']} {category.replace('_', ' ')}"
    k = settings.top_k + (2 if attempt > 0 else 0)
    if attempt > 0:
        query = f"{state['subject']} {query}"
    passages = store.search(query, k)

    agreement = store.agreement(passages[:settings.top_k])
    cats = [p["category"] for p in passages[:settings.top_k]]
    disagreement = 0.0 if not cats else 1 - Counter(cats).most_common(1)[0][1] / len(cats)
    top = passages[0]["score"] if passages else 0.0
    evidence = [{"id": p["id"], "title": p["title"], "content": p["content"], "category": p["category"],
                 "source": p["source"], "score": p["score"]} for p in passages]
    return {"evidence": evidence,
            "retrieval": {"top_score": top, "agreement": round(agreement, 3),
                          "disagreement": round(disagreement, 3), "k": k, "attempt": attempt},
            "_summary": f"{len(evidence)} passages · top cosine {top:.2f} · attempt {attempt + 1}"}
