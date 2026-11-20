"""Triage Agent: category c_i, urgency u_i in [0,1], sentiment s_i in [-1,1], priority P_i (Eq. 3)."""
import math
import re

from ..config import settings
from .base import AgentSpec, clip

SPEC = AgentSpec(
    "triage", "Support Triage Specialist",
    "Classify every incoming ticket by category, urgency and sentiment and score its priority.",
    "A veteran queue manager who has seen thousands of tickets and never misses a locked-out or angry customer.")

# keyword -> weight; each keyword matches as a word prefix so plurals/tenses are covered
CATEGORY_KEYWORDS: dict[str, dict[str, float]] = {
    "account_security": {"password": 3, "login": 3, "log in": 3, "sign in": 3, "locked": 3, "two-factor": 3,
                         "2fa": 3, "verification code": 3, "hacked": 3, "suspicious": 2,
                         "authenticat": 2, "reset": 1},
    "billing": {"invoice": 3, "charge": 2.5, "billing": 3, "payment": 2, "subscription": 2, "renew": 2,
                "receipt": 2.5, "card": 1, "overcharg": 3, "price": 1, "tax": 2, "plan": 1, "transaction": 2},
    "returns_refunds": {"refund": 4, "return": 3, "exchange": 3, "money back": 4, "damaged": 3,
                        "defective": 3, "wrong item": 3, "replacement": 2.5, "broken item": 3},
    "shipping": {"delivery": 3, "deliver": 2, "shipping": 3, "track": 3, "package": 2.5, "shipped": 2,
                 "arrive": 2, "courier": 2, "where is my": 3, "order": 1.5, "parcel": 2.5},
    "technical": {"error": 3, "bug": 3, "crash": 3, "not working": 3, "freez": 3, "loading": 2,
                  "fails": 2, "failed": 1.5, "api": 2.5, "401": 3, "integration": 2, "app": 1, "website": 1.5,
                  "notification": 2, "slow": 1.5, "page": 1},
    "account_management": {"email address": 3, "phone number": 3, "update my": 2.5, "change my": 3,
                           "profile": 2, "delete my account": 5, "close my account": 5, "username": 2,
                           "my address": 2},
    "general": {"hours": 2, "contact": 1.5, "human": 2, "agent": 1, "support": 0.5, "talk to": 2},
}

CATEGORY_WEIGHT = {"account_security": 0.9, "billing": 0.8, "returns_refunds": 0.6, "shipping": 0.5,
                   "technical": 0.5, "account_management": 0.4, "general": 0.2}

NEGATIVE = {"angry", "furious", "terrible", "awful", "worst", "horrible", "unacceptable", "ridiculous",
            "disappointed", "frustrat", "annoy", "useless", "scam", "fraud", "never", "still", "again",
            "waiting", "stuck", "broken", "fail", "problem", "issue", "complain", "disgust", "angry",
            "charged twice", "double charged", "lawyer", "legal", "unauthorized charge", "unauthorized transaction", "hacked", "stolen",
            "damaged", "wrong", "late", "missing", "lost", "cannot", "can't", "won't", "not working"}
POSITIVE = {"thanks", "thank", "great", "love", "awesome", "appreciate", "happy", "excellent", "good",
            "perfect", "helpful", "pleased", "wonderful"}
URGENT = {"urgent", "asap", "immediately", "right now", "emergency", "today", "locked out", "fraud",
          "unauthorized charge", "unauthorized transaction", "hacked", "stolen", "deadline", "cannot access", "can't access", "critical",
          "charged twice", "double charged", "lawyer", "legal"}


def _hits(text: str, vocab) -> int:
    return sum(1 for w in vocab if re.search(r"(?<![a-z])" + re.escape(w), text))


def classify(text: str) -> tuple[str, dict[str, float]]:
    scores = {c: 0.0 for c in CATEGORY_KEYWORDS}
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw, w in kws.items():
            if re.search(r"(?<![a-z])" + re.escape(kw), text):
                scores[cat] += w
    best = max(scores, key=scores.get)
    return (best if scores[best] > 0 else "general"), scores


def sentiment(raw: str) -> float:
    t = raw.lower()
    neg, pos = _hits(t, NEGATIVE), _hits(t, POSITIVE)
    caps = len(re.findall(r"\b[A-Z]{3,}\b", raw))
    if neg:
        neg += min(caps, 2) * 0.5 + min(raw.count("!"), 3) * 0.3
    return round(math.tanh((pos - neg) / 2.0), 3)


def urgency(raw: str, s: float) -> float:
    t = raw.lower()
    u = 0.10 + 0.22 * _hits(t, URGENT) + 0.25 * max(0.0, -s) + 0.05 * min(raw.count("!"), 2)
    return round(clip(u), 3)


def priority(u: float, s: float, category: str) -> float:
    """Eq. (3): P = alpha*u + beta*(1 - (s+1)/2) + gamma*w_c(c)."""
    p = settings.alpha * u + settings.beta * (1 - (s + 1) / 2) + settings.gamma * CATEGORY_WEIGHT[category]
    return round(clip(p), 3)


def run(state: dict) -> dict:
    raw = f"{state['subject']}. {state['text']}"
    category, scores = classify(raw.lower())
    s = sentiment(raw)
    u = urgency(raw, s)
    p = priority(u, s, category)
    return {"triage": {"category": category, "urgency": u, "sentiment": s, "priority": p,
                       "category_scores": {k: round(v, 2) for k, v in scores.items() if v > 0}},
            "_summary": f"{category} · urgency {u:.2f} · sentiment {s:+.2f} · priority {p:.2f}"}
