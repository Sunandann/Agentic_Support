"""Runtime configuration. Every coefficient from the paper is tunable via env vars."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _f(name: str, default: float) -> float:
    return float(os.getenv(name, default))


class Settings:
    def __init__(self) -> None:
        default_db = "/tmp/support.db" if os.getenv("VERCEL") == "1" else str(BASE_DIR / "support.db")
        self.database_url = os.getenv("DATABASE_URL", f"sqlite:///{default_db}")
        self.top_k = int(os.getenv("TOP_K", 3))
        # Eq. (3) composite priority weights (alpha + beta + gamma = 1)
        self.alpha = _f("TRIAGE_ALPHA", 0.45)
        self.beta = _f("TRIAGE_BETA", 0.30)
        self.gamma = _f("TRIAGE_GAMMA", 0.25)
        # Eq. (5) escalation weights (lambda1 + lambda2 + lambda3 = 1) and Eq. (6) threshold
        self.lam1 = _f("ESC_LAMBDA1", 0.50)
        self.lam2 = _f("ESC_LAMBDA2", 0.30)
        self.lam3 = _f("ESC_LAMBDA3", 0.20)
        self.tau = _f("ESC_TAU", 0.50)
        # Cosine similarity at which retrieval is treated as "fully confident"
        self.sim_ref = _f("SIM_REF", 0.35)
        self.max_retries = int(os.getenv("MAX_RETRIES", 1))
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "")
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.cors_origins = [o.strip() for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]


settings = Settings()
