<div align="center">

# 🎧 Support Desk
### Agentic AI for Automated Customer Support and Ticket Resolution

*Four agents resolve what is safe, and hand over what is not.*

[![Live Demo](https://img.shields.io/badge/Live_Demo-Visit_Site-935073?style=for-the-badge&logo=vercel&logoColor=white)](https://frontend-eosin-pi-10.vercel.app)

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat-square)
![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square)
![Works Offline](https://img.shields.io/badge/Works-Offline-935073?style=flat-square)

<br />

<img src="docs/dashboard.png" alt="Support Desk dashboard" width="900" />

</div>

---

## ✨ What is this?

A working implementation of the paper's **Orchestrator–Worker multi-agent architecture** with grounded retrieval and confidence-based escalation.

A customer ticket comes in. Four specialised agents handle it in milliseconds. Safe, well-supported answers are sent automatically. Anything risky or uncertain is handed to a human, with the full decision trail attached.

```
ticket → FastAPI → LangGraph orchestrator → Triage → Retrieval → Resolution → Escalation
                                                          ▲                       │
                                                          └────── retry ──────────┤
                                                    auto-resolve ◄── X ≤ τ ── X > τ ──► human (full trail)
```

## 🚀 Highlights

| | Feature | What it does |
|---|---|---|
| 🧭 | **Triage agent** | Detects category, urgency and sentiment, then computes a priority score |
| 🔎 | **Retrieval agent** | Finds the most relevant knowledge-base passages (top-k cosine similarity) |
| ✍️ | **Resolution agent** | Drafts a reply grounded only in retrieved evidence and runs bounded routine actions |
| 🚦 | **Escalation agent** | Scores confidence and complexity, then auto-resolves or hands off to a human |
| 🧾 | **Audit trail** | Every agent step is logged and the ticket state is checkpointed |
| 📊 | **Dashboard** | Live queue, charts, agent activity, and a feedback loop for the team |
| 📴 | **Fully offline** | No API key, no model downloads, SQLite by default |

## 🖥️ Quick start (about 2 minutes)

**1. Backend** (Python 3.10+)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000              # API docs: http://127.0.0.1:8000/docs
```

**2. Dashboard** (Node 18+), in a second terminal
```bash
cd frontend
npm install
npm run dev                                            # http://localhost:5173
```

**3. Try it.** Open the dashboard and click **Load sample tickets**, or send your own from the Overview tab. It works fully offline.

## 🗺️ Paper → code map

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

## 🔌 API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/tickets` | Submit a ticket |
| `GET` | `/api/tickets[?status=]` | List tickets |
| `GET` | `/api/tickets/{id}` | One ticket with evidence and agent trail |
| `POST` | `/api/tickets/{id}/resolve` | Close an escalated ticket |
| `GET` | `/api/stats` | Dashboard metrics |
| `GET` / `POST` | `/api/kb` | Read or add knowledge-base passages |
| `POST` | `/api/feedback/run` | Run the feedback loop |
| `POST` | `/api/demo/seed` | Load sample tickets |
| `GET` | `/api/health` | Health check |

## 🧪 Tests and evaluation

```bash
cd backend
python -m pytest -q                       # 20 unit + pipeline + API tests
python -m scripts.evaluate --verbose      # triage P/R/F1, FCR, escalation precision/recall, latency
python -m scripts.evaluate --tau 0.4      # sweep τ to trade resolution rate against safety
```
> Escalation precision in the dashboard becomes meaningful once team members close escalated tickets and tick "this really needed a human".

## 🔧 Optional upgrades

- **LLM-drafted replies:** `pip install -r requirements-optional.txt`, then set `LLM_API_KEY` (and `LLM_BASE_URL` / `LLM_MODEL` for any OpenAI-compatible endpoint). The prompt only allows answers from retrieved evidence. With an LLM, self-consistency is measured over 3 sampled drafts.
- **MySQL:** `docker compose up -d`, then set `DATABASE_URL=mysql+pymysql://support:supportpass@127.0.0.1:3306/support_ai`. Tables are created at startup.
- **Dense embeddings / FAISS / Chroma / Pinecone:** replace the TF-IDF internals of `VectorStore` in `knowledge.py`; the `search()` contract stays the same.

## ☁️ Deployment

Both apps are deployed on Vercel as separate projects (`frontend` and `backend`). For the frontend, set the environment variable `VITE_API_URL` to your deployed backend address (no trailing slash), then redeploy.

## 📝 Where this implementation differs from the paper's wording

Keep the paper and the code consistent before you submit:

1. **ORM:** Sequelize is a Node.js ORM and cannot be used from a Python FastAPI backend. This project uses **SQLAlchemy** against MySQL (or SQLite).
2. **CrewAI:** each agent has a CrewAI-style spec (role, goal, backstory, one responsibility, bound to its own tool) but is plain Python; CrewAI is **not** a dependency. LangGraph is used for orchestration, with a sequential fallback if it is missing.
3. **Embeddings:** default is TF-IDF cosine (offline, deterministic), not a neural embedding model or LangChain RAG.
4. **Triage** is keyword/lexicon based, not an LLM or trained classifier.
5. **Offline self-consistency** is approximated by agreement between the retrieved passages; sampled-draft agreement is used only when an LLM is configured.
6. **Backend actions** (password reset, refund, account update) are simulated in `services.py` and only write audit rows.
7. **Evaluation numbers** from the bundled 38-ticket synthetic set are smoke-test figures. The rules were tuned while looking at that set, so do not report them as deployment results; collect a held-out set first.

---

<div align="center">

Built with FastAPI, LangGraph, React and Tailwind CSS.

</div>
