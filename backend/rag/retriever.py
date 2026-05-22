"""Search interview experiences in Qdrant."""
import requests
from sentence_transformers import CrossEncoder

from core.config import settings
from rag.embedder import embed
from rag.schema import COLLECTION_NAME

RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_encoder: CrossEncoder | None = None



_encoder_failed = False


def _get_encoder() -> CrossEncoder | None:
    global _encoder, _encoder_failed
    if _encoder_failed:
        return None
    if _encoder is None:
        try:
            _encoder = CrossEncoder(RERANK_MODEL)
        except Exception:
            _encoder_failed = True
            return None
    return _encoder


def _search(query_vector: list[float], limit: int, filters: dict | None) -> list[dict]:
    body: dict = {"vector": query_vector, "limit": limit, "with_payload": True}
    if filters:
        body["filter"] = filters

    url = f"{settings.qdrant_url}/collections/{COLLECTION_NAME}/points/search"
    resp = requests.post(url, json=body)
    resp.raise_for_status()
    return resp.json().get("result", [])


def retrieve(
    query: str,
    company: str | None = None,
    position: str | None = None,
    difficulty: str | None = None,
    limit: int = 5,
    rerank_top_n: int = 20,
) -> list[dict]:
    """Search interview experience chunks relevant to query."""
    query_vector = embed(query)

    must: list[dict] = []
    if company:
        must.append({"key": "company", "match": {"text": company}})
    if position:
        must.append({"key": "position", "match": {"text": position}})
    if difficulty:
        must.append({"key": "difficulty", "match": {"value": difficulty}})

    qdrant_filter = {"must": must} if must else None
    results = _search(query_vector, limit=rerank_top_n, filters=qdrant_filter)

    if not results:
        return []

    encoder = _get_encoder()
    if encoder is not None:
        candidates = [(hit.get("payload", {}).get("search_text", ""), query) for hit in results]
        scores = encoder.predict(candidates)
        ranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)
    else:
        ranked = [(hit, hit.get("score", 0)) for hit in results]

    return [
        {
            "chunk_id": hit.get("payload", {}).get("chunk_id"),
            "chunk_type": hit.get("payload", {}).get("chunk_type", "sliding_window"),
            "question": hit.get("payload", {}).get("question", ""),
            "answer": hit.get("payload", {}).get("answer", ""),
            "raw_text": hit.get("payload", {}).get("raw_text", ""),
            "search_text": hit.get("payload", {}).get("search_text", ""),
            "company": hit.get("payload", {}).get("company", ""),
            "position": hit.get("payload", {}).get("position", ""),
            "round": hit.get("payload", {}).get("round", ""),
            "date": hit.get("payload", {}).get("date", ""),
            "source_file": hit.get("payload", {}).get("source_file", ""),
            "score": round(float(score), 4),
        }
        for hit, score in ranked[:limit]
    ]
