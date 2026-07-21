"""RAG pipeline: chunk the clinic knowledge base by section, embed with Gemini,
retrieve top-k sections by cosine similarity. Embeddings are cached on disk and
invalidated by a content hash, so the KB can be swapped per-client with zero code
changes. A keyword-overlap fallback keeps the demo alive if the embedding API is
unavailable (quota, network)."""

import hashlib
import json
import re
from pathlib import Path

import numpy as np
from google import genai
from google.genai import types

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768

DATA_DIR = Path(__file__).parent / "data"
KB_PATH = DATA_DIR / "riverstone_family_health_kb.md"
CACHE_PATH = DATA_DIR / "kb_embeddings.json"


def load_chunks(kb_path: Path = KB_PATH) -> list[dict]:
    """Split the markdown KB into one chunk per '## ' section."""
    text = kb_path.read_text(encoding="utf-8")
    parts = re.split(r"\n(?=## )", text)
    chunks = []
    for part in parts:
        part = part.strip().strip("-").strip()
        if len(part) < 40:
            continue
        first_line = part.splitlines()[0]
        title = first_line.lstrip("#").strip() or "General"
        chunks.append({"title": title, "text": part})
    return chunks


def _kb_hash(chunks: list[dict]) -> str:
    joined = "\n".join(c["text"] for c in chunks)
    return hashlib.md5(joined.encode("utf-8")).hexdigest()


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class Retriever:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.chunks = load_chunks()
        self.vectors: np.ndarray | None = None
        self._load_or_build_index()

    # ---------------- index ----------------

    def _load_or_build_index(self) -> None:
        kb_hash = _kb_hash(self.chunks)
        if CACHE_PATH.exists():
            try:
                cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
                if cache.get("hash") == kb_hash:
                    self.vectors = _normalize(np.array(cache["vectors"], dtype=np.float32))
                    return
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        try:
            self._build_index(kb_hash)
        except Exception:
            # Embedding failed (bad key, quota, offline) — keyword fallback will be used.
            self.vectors = None

    def _build_index(self, kb_hash: str) -> None:
        result = self.client.models.embed_content(
            model=EMBED_MODEL,
            contents=[c["text"] for c in self.chunks],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=EMBED_DIM,
            ),
        )
        vectors = np.array([e.values for e in result.embeddings], dtype=np.float32)
        CACHE_PATH.write_text(
            json.dumps({"hash": kb_hash, "vectors": vectors.tolist()}),
            encoding="utf-8",
        )
        self.vectors = _normalize(vectors)

    # ---------------- retrieval ----------------

    def retrieve(self, query: str, k: int = 4) -> list[dict]:
        """Return the top-k most relevant KB sections for a query."""
        if self.vectors is not None:
            try:
                return self._semantic_search(query, k)
            except Exception:
                pass
        return self._keyword_search(query, k)

    def _semantic_search(self, query: str, k: int) -> list[dict]:
        result = self.client.models.embed_content(
            model=EMBED_MODEL,
            contents=[query],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=EMBED_DIM,
            ),
        )
        qvec = _normalize(np.array([result.embeddings[0].values], dtype=np.float32))[0]
        scores = self.vectors @ qvec
        top = np.argsort(scores)[::-1][:k]
        return [
            {**self.chunks[i], "score": float(scores[i]), "method": "semantic"}
            for i in top
        ]

    def _keyword_search(self, query: str, k: int) -> list[dict]:
        query_terms = set(re.findall(r"[a-z]+", query.lower())) - _STOPWORDS
        scored = []
        for chunk in self.chunks:
            chunk_terms = set(re.findall(r"[a-z]+", chunk["text"].lower()))
            overlap = len(query_terms & chunk_terms)
            scored.append((overlap, chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            {**chunk, "score": float(score), "method": "keyword"}
            for score, chunk in scored[:k]
            if score > 0
        ] or [{**self.chunks[0], "score": 0.0, "method": "keyword"}]


_STOPWORDS = {
    "the", "a", "an", "is", "are", "do", "does", "can", "i", "you", "we",
    "what", "how", "when", "where", "my", "your", "to", "of", "for", "in",
    "on", "at", "and", "or", "it", "me", "with", "have", "has",
}
