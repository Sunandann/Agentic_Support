# Agentic AI for Automated Customer Support and Ticket Resolution

Working implementation of the paper's **Orchestrator–Worker multi-agent architecture** with grounded retrieval and confidence-based escalation.

```
ticket → FastAPI → LangGraph orchestrator → Triage → Retrieval → Resolution → Escalation
                                                          ▲                       │
                                                          └────── retry ──────────┤
                                                    auto-resolve ◄── X ≤ τ ── X > τ ──► human (full trail)
```

## Run it (about 2 minutes)

**Backend** (Python 3.10+)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000              # API docs: http://127.0.0.1:8000/docs
```

**Dashboard** (Node 18+), in a second terminal
```bash
cd frontend
npm install
npm run dev                                            # http://localhost:5173
```
Open the dashboard and click **Load sample tickets**, or send your own from the Overview tab.

It works fully offline: no API key, no model downloads, SQLite by default.

## Paper → code map

| Paper | Where |
|---|---|
| Orchestrator, state graph G=(V,E), δ transition (Eq. 2), predicate ρ, checkpoints | `backend/app/orchestrator.py` |
| Triage: category, urgency, sentiment, priority P (Eq. 3) | `backend/app/agents/triage.py` |
| Retrieval: top-k cosine similarity (Eq. 4), vector store V | `backend/app/agents/retrieval.py`, `backend/app/knowledge.py` |
| Resolution: grounded draft, bounded `A_routine` actions | `backend/app/agents/resolution.py`, `backend/app/services.py` |
| Escalation: Conf, Cplx, score X (Eq. 5), threshold τ (Eq. 6), hard rules | `backend/app/agents/escalation.py` |
| Audit log, persistence (Sec. III-H) | `backend/app/models.py` (`AgentLog`, `Ticket.state`) |
| Dashboard and feedback loop (Sec. III-I) | `frontend/`, `POST /api/feedback/run`, resolve endpoint |
| Evaluation framework (Sec. V, Table III) | `backend/scripts/evaluate.py`, `GET /api/stats`, `backend/tests/` |

All coefficients (α, β, γ, λ₁–λ₃, τ, top-k) are environment variables, see `backend/.env.example`.

## API

`POST /api/tickets` · `GET /api/tickets[?status=]` · `GET /api/tickets/{id}` (with evidence and agent trail) · `POST /api/tickets/{id}/resolve` · `GET /api/stats` · `GET/POST /api/kb` · `POST /api/feedback/run` · `POST /api/demo/seed` · `GET /api/health`

## Tests and evaluation

```bash
cd backend
python -m pytest -q                       # 20 unit + pipeline + API tests
python -m scripts.evaluate --verbose      # triage P/R/F1, FCR, escalation precision/recall, latency
python -m scripts.evaluate --tau 0.4      # sweep τ to trade resolution rate against safety
```
Escalation precision in the dashboard becomes meaningful once team members close escalated tickets and tick "this really needed a human".

## Optional upgrades

* **LLM-drafted replies:** `pip install -r requirements-optional.txt`, then set `LLM_API_KEY` (and `LLM_BASE_URL` / `LLM_MODEL` for any OpenAI-compatible endpoint). The prompt only allows answers from retrieved evidence. With an LLM, self-consistency is measured over 3 sampled drafts.
* **MySQL:** `docker compose up -d`, then set `DATABASE_URL=mysql+pymysql://support:supportpass@127.0.0.1:3306/support_ai`. Tables are created at startup.
* **Dense embeddings / FAISS / Chroma / Pinecone:** replace the TF-IDF internals of `VectorStore` in `knowledge.py`; the `search()` contract stays the same.

## Where this implementation differs from the paper's wording

Keep the paper and the code consistent before you submit:

1. **ORM:** Sequelize is a Node.js ORM and cannot be used from a Python FastAPI backend. This project uses **SQLAlchemy** against MySQL (or SQLite).
2. **CrewAI:** each agent has a CrewAI-style spec (role, goal, backstory, one responsibility, bound to its own tool) but is plain Python; CrewAI is **not** a dependency. LangGraph is used for orchestration, with a sequential fallback if it is missing.
3. **Embeddings:** default is TF-IDF cosine (offline, deterministic), not a neural embedding model or LangChain RAG.
4. **Triage** is keyword/lexicon based, not an LLM or trained classifier.
5. **Offline self-consistency** is approximated by agreement between the retrieved passages; sampled-draft agreement is used only when an LLM is configured.
6. **Backend actions** (password reset, refund, account update) are simulated in `services.py` and only write audit rows.
7. **Evaluation numbers** from the bundled 38-ticket synthetic set are smoke-test figures. The rules were tuned while looking at that set, so do not report them as deployment results; collect a held-out set first.
