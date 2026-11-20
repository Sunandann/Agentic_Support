"""Vector store V (paper Eq. 4): cosine similarity over TF-IDF embeddings phi(.).

TF-IDF keeps the project runnable offline with zero model downloads. To use dense
embeddings, replace `_embed` / `_fit` with a sentence-transformer + FAISS/Chroma index;
the `search()` contract stays identical.
"""
import json
import threading

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy.orm import Session

from .config import DATA_DIR
from .models import KnowledgeDoc


class VectorStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._docs: list[dict] = []
        self._vec: TfidfVectorizer | None = None
        self._matrix = None

    def rebuild(self, docs: list[dict]) -> None:
        with self._lock:
            self._docs = docs
            if not docs:
                self._vec, self._matrix = None, None
                return
            self._vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                        sublinear_tf=True, min_df=1)
            self._matrix = self._vec.fit_transform([f"{d['title']} {d['content']}" for d in docs])

    def __len__(self) -> int:
        return len(self._docs)

    def search(self, query: str, k: int = 3) -> list[dict]:
        """Top-k passages by cosine similarity (TF-IDF rows are L2-normalised)."""
        with self._lock:
            if self._vec is None or not self._docs:
                return []
            q = self._vec.transform([query])
            sims = (self._matrix @ q.T).toarray().ravel()
            order = np.argsort(-sims)[:k]
            return [{**self._docs[i], "score": round(float(sims[i]), 4)} for i in order if sims[i] > 0]

    def agreement(self, passages: list[dict]) -> float:
        """Mean pairwise cosine between retrieved passages (support-consistency proxy)."""
        with self._lock:
            if self._vec is None or len(passages) < 2:
                return 1.0 if passages else 0.0
            m = self._vec.transform([f"{p['title']} {p['content']}" for p in passages])
            s = (m @ m.T).toarray()
            n = len(passages)
            return float((s.sum() - n) / (n * (n - 1)))

    def text_similarity(self, a: str, b: str) -> float:
        with self._lock:
            if self._vec is None:
                return 0.0
            m = self._vec.transform([a, b])
            return float((m[0] @ m[1].T).toarray()[0, 0])


store = VectorStore()


def load_store(db: Session) -> None:
    docs = db.query(KnowledgeDoc).order_by(KnowledgeDoc.id).all()
    store.rebuild([d.to_dict() for d in docs])


def seed_knowledge(db: Session) -> int:
    """Insert the seed FAQ/doc corpus if the knowledge base is empty."""
    if db.query(KnowledgeDoc).count() == 0:
        for item in json.loads((DATA_DIR / "kb_seed.json").read_text(encoding="utf-8")):
            db.add(KnowledgeDoc(**item))
        db.commit()
    load_store(db)
    return len(store)


def add_doc(db: Session, title: str, content: str, category: str, source: str,
            ticket_id: int | None = None) -> KnowledgeDoc:
    doc = KnowledgeDoc(title=title[:255], content=content, category=category,
                       source=source, ticket_id=ticket_id)
    db.add(doc)
    db.commit()
    load_store(db)
    return doc
