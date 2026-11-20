import json

import pytest

from app.agents import escalation, resolution, retrieval, triage
from app.config import DATA_DIR, settings
from app.knowledge import store
from app.orchestrator import run_pipeline


@pytest.fixture(autouse=True, scope="module")
def kb():
    seed = json.loads((DATA_DIR / "kb_seed.json").read_text(encoding="utf-8"))
    store.rebuild([{**d, "id": i + 1} for i, d in enumerate(seed)])


STUB = lambda a, p: {"executed": True, "detail": f"{a} done", "reference": "T-1"}


# ---- Triage (Eq. 3) --------------------------------------------------------
def test_triage_categories():
    cases = {"I forgot my password": "account_security", "Where is my package? Tracking is stuck": "shipping",
             "I want a refund for the wrong item": "returns_refunds", "Send me the invoice for my payment": "billing",
             "The app crashes with an error": "technical"}
    for text, cat in cases.items():
        assert triage.run({"subject": "", "text": text})["triage"]["category"] == cat


def test_triage_ranges_and_priority_formula():
    t = triage.run({"subject": "URGENT", "text": "I was charged twice and I am furious!!"})["triage"]
    assert 0 <= t["urgency"] <= 1 and -1 <= t["sentiment"] <= 1 and 0 <= t["priority"] <= 1
    assert t["sentiment"] < 0
    expected = (settings.alpha * t["urgency"] + settings.beta * (1 - (t["sentiment"] + 1) / 2)
                + settings.gamma * triage.CATEGORY_WEIGHT[t["category"]])
    assert t["priority"] == pytest.approx(expected, abs=1e-3)


def test_angry_ticket_has_higher_priority_than_calm_one():
    calm = triage.run({"subject": "", "text": "How do I download my invoice?"})["triage"]
    angry = triage.run({"subject": "", "text": "This is URGENT! I was charged twice, terrible service!"})["triage"]
    assert angry["priority"] > calm["priority"]


# ---- Retrieval (Eq. 4) -----------------------------------------------------
def test_retrieval_returns_relevant_sorted_evidence():
    out = retrieval.run({"subject": "Password", "text": "how do I reset my password", "attempt": 0,
                         "triage": {"category": "account_security"}})
    ev = out["evidence"]
    assert ev and ev[0]["category"] == "account_security"
    assert [e["score"] for e in ev] == sorted((e["score"] for e in ev), reverse=True)
    assert len(ev) <= settings.top_k


def test_retrieval_retry_widens_search():
    base = {"subject": "x", "text": "package", "triage": {"category": "shipping"}}
    assert retrieval.run({**base, "attempt": 1})["retrieval"]["k"] == settings.top_k + 2


# ---- Resolution ------------------------------------------------------------
def test_action_detection_and_restricted_requests():
    assert resolution.detect_action("I forgot my password")[0] == "password_reset"
    action, _, params = resolution.detect_action("refund for ORD-12345 please")
    assert action == "refund_initiation" and params["order_id"] == "ORD-12345"
    assert resolution.detect_action("delete my account now")[1] is True
    assert resolution.detect_action("my API returns 401 unauthorized")[1] is False


def test_restricted_request_never_executes_actions():
    calls = []
    s = run_pipeline("", "I will sue you, refund me and delete my account", lambda a, p: calls.append(a) or STUB(a, p))
    assert calls == [] and s["decision"] == "escalate"


# ---- Escalation (Eq. 5-6) --------------------------------------------------
def test_escalation_score_matches_formula():
    state = {"triage": {"urgency": 0.4}, "retrieval": {"top_score": 0.3, "agreement": 0.2, "disagreement": 0.3},
             "resolution": {"out_of_scope": False, "samples": None}, "evidence": [{"x": 1}], "attempt": 0}
    e = escalation.run(state)["escalation"]
    x = settings.lam1 * (1 - e["confidence"]) + settings.lam2 * e["complexity"] + settings.lam3 * 0.4
    assert e["score"] == pytest.approx(x, abs=1e-3)


def test_escalation_hard_rules():
    base = {"triage": {"urgency": 0.1}, "retrieval": {"top_score": 0.9, "agreement": 1, "disagreement": 0},
            "resolution": {"out_of_scope": True, "samples": None}, "evidence": [{"x": 1}], "attempt": 0}
    assert escalation.run(base)["escalation"]["route"] == "escalate"
    no_ev = {**base, "resolution": {"out_of_scope": False, "samples": None}, "evidence": []}
    assert escalation.run(no_ev)["escalation"]["route"] == "escalate"


# ---- Whole pipeline --------------------------------------------------------
def test_pipeline_auto_resolves_routine_ticket_with_action():
    s = run_pipeline("Locked out", "I forgot my password and cannot log in.", STUB)
    assert s["decision"] == "auto-resolve" and s["resolution"]["action"] == "password_reset"
    assert "reset" in s["resolution"]["reply"].lower()


def test_pipeline_escalates_nonsense_and_legal():
    assert run_pipeline("", "asdf qwer zxcv blorp", STUB)["decision"] == "escalate"
    assert run_pipeline("", "I am contacting my lawyer about this", STUB)["decision"] == "escalate"


def test_retry_loop_executes_actions_only_once():
    calls = []
    run_pipeline("", "refund order ORD-99999 please but also the weather is nice and my cat likes tuna",
                 lambda a, p: calls.append(a) or STUB(a, p))
    assert len(calls) <= 1
