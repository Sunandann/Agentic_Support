"""Offline evaluation harness for the metrics in Section V / Table III of the paper.

Runs the real pipeline (no database) over a labelled ticket set and reports triage
precision/recall/F1, retrieval hit-rate, first-contact resolution, escalation precision/recall,
and per-ticket latency. Run:  python -m scripts.evaluate [--tau 0.5] [--file data/eval_tickets.json]
NOTE: numbers on the bundled set are on small synthetic data and are for smoke-testing only.
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.knowledge import store  # noqa: E402
from app.orchestrator import run_pipeline  # noqa: E402


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "data" / "eval_tickets.json"))
    ap.add_argument("--tau", type=float, default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    if args.tau is not None:
        settings.tau = args.tau

    seed = json.loads((ROOT / "data" / "kb_seed.json").read_text(encoding="utf-8"))
    store.rebuild([{**d, "id": i + 1} for i, d in enumerate(seed)])
    tickets = json.loads(Path(args.file).read_text(encoding="utf-8"))

    stub = lambda a, p: {"executed": True, "detail": f"{a} simulated", "reference": "SIM-0000"}
    cats = sorted({t["category"] for t in tickets})
    tp, fp, fn = defaultdict(int), defaultdict(int), defaultdict(int)
    hits = auto_n = esc_tp = esc_n = esc_missed = 0
    lat, rows = [], []

    for t in tickets:
        t0 = time.perf_counter()
        s = run_pipeline(t["subject"], t["body"], stub)
        lat.append((time.perf_counter() - t0) * 1000)
        pred, gold = s["triage"]["category"], t["category"]
        for c in cats:
            tp[c] += pred == c and gold == c
            fp[c] += pred == c and gold != c
            fn[c] += pred != c and gold == c
        top_cat = s["evidence"][0]["category"] if s["evidence"] else None
        hits += top_cat == gold
        is_esc = s["decision"] == "escalate"
        auto_n += not is_esc
        esc_n += is_esc
        esc_tp += is_esc and t["expected_decision"] == "escalate"
        esc_missed += (not is_esc) and t["expected_decision"] == "escalate"
        rows.append((t["subject"], gold, pred, t["expected_decision"], s["decision"], s["escalation"]["score"]))

    n = len(tickets)
    print(f"\nTickets: {n}   tau={settings.tau}   mode={'LLM' if settings.llm_api_key else 'offline'}\n")
    print(f"{'category':20s} {'P':>6s} {'R':>6s} {'F1':>6s}")
    f1s = []
    for c in cats:
        p, r, f = prf(tp[c], fp[c], fn[c])
        f1s.append(f)
        print(f"{c:20s} {p:6.2f} {r:6.2f} {f:6.2f}")
    acc = sum(tp.values()) / n
    print(f"{'macro-F1':20s} {'':6s} {'':6s} {sum(f1s) / len(f1s):6.2f}      accuracy {acc:.2f}")
    esc_gold = sum(1 for t in tickets if t["expected_decision"] == "escalate")
    print(f"\nRetrieval hit-rate (top passage in the right category): {hits / n:.2%}")
    print(f"First-contact resolution rate:                          {auto_n / n:.2%}")
    print(f"Escalation precision:                                   {esc_tp / esc_n if esc_n else 0:.2%}")
    print(f"Escalation recall (unsafe tickets caught):              {esc_tp / esc_gold if esc_gold else 0:.2%}")
    print(f"Unsafe tickets auto-resolved (missed escalations):      {esc_missed}")
    srt = sorted(lat)
    print(f"Pipeline latency  mean {sum(lat) / n:.1f} ms   p95 {srt[int(0.95 * (n - 1))]:.1f} ms")
    if args.verbose:
        print("\nsubject | gold cat | pred cat | expected | decision | X")
        for r in rows:
            flag = "" if (r[1] == r[2] and (r[3] == "escalate") == (r[4] == "escalate")) else "  <--"
            print(f"{r[0][:24]:24s} {r[1]:18s} {r[2]:18s} {r[3]:8s} {r[4]:12s} {r[5]:.2f}{flag}")


if __name__ == "__main__":
    main()
