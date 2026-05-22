"""Local embedding — no API key needed. Uses all-MiniLM-L6-v2."""
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-zh-v1.5"

_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(MODEL_NAME)
    return _embedder


def embed(text: str) -> list[float]:
    return get_embedder().encode(text).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    return get_embedder().encode(texts).tolist()
