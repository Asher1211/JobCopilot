"""Index interview experience files into Qdrant.

Pipeline:
  1. Extract text from .docx/.pdf/.txt
  2. (optional) LLM preprocess: extract Q&A pairs
     - if Q&A found → one chunk per Q&A pair
     - if not → sliding window fallback
  3. Embed searchable text
  4. Store in Qdrant with metadata

Usage:
    python -m rag.indexer <file>              # sliding window only
    python -m rag.indexer <file> --preprocess # LLM Q&A extraction
"""
import asyncio
import os
import sys
from pathlib import Path

import requests

from core.config import settings
from rag.chunker import extract_text, sliding_window
from rag.embedder import embed_batch
from rag.preprocessor import preprocess
from rag.schema import COLLECTION_NAME, DISTANCE_METRIC, VECTOR_SIZE

BASE = f"{settings.qdrant_url}/collections/{COLLECTION_NAME}"


async def index_file(
    file_path: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "deepseek-chat",
    use_llm: bool = False,
) -> int:
    path = Path(file_path)
    name = path.name
    print(f"File: {name} ({path.suffix})")

    raw = path.read_bytes()
    text = extract_text(raw, name)
    print(f"  Text: {len(text)} chars")

    # ── Step 1: Try LLM Q&A extraction ──
    meta = {"company": "", "position": "", "round": "", "date": ""}
    qa_pairs: list[dict] = []

    if use_llm and api_key:
        print("  LLM: extracting Q&A pairs...")
        result = await preprocess(text, api_key, base_url, model)
        meta = {
            "company": result.get("company", ""),
            "position": result.get("position", ""),
            "round": result.get("round", ""),
            "date": result.get("date", ""),
        }
        qa_pairs = result.get("qa_pairs", [])
        print(f"  Found {len(qa_pairs)} Q&A pairs, company={meta['company']}, position={meta['position']}")

    # ── Step 2: Build chunks ──
    if qa_pairs:
        chunks = _build_qa_chunks(qa_pairs, meta, name)
    else:
        print("  No Q&A pairs, using sliding window fallback")
        raw_chunks = sliding_window(text)
        chunks = _build_sw_chunks(raw_chunks, meta, name)

    if not chunks:
        print("  No chunks to index")
        return 0

    # ── Step 3: Embed & upload ──
    search_texts = [c["search_text"] for c in chunks]
    print(f"  Embedding {len(chunks)} chunks...")
    embeddings = embed_batch(search_texts)

    points = [
        {"id": i + 1, "vector": emb, "payload": c}
        for i, (c, emb) in enumerate(zip(chunks, embeddings))
    ]

    batch_size = 20
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        resp = requests.put(f"{BASE}/points", json={"points": batch})
        if resp.status_code != 200:
            print(f"  Batch {i // batch_size + 1} error: {resp.status_code} {resp.text[:200]}")
            return 0
        print(f"  Batch {i // batch_size + 1}/{(len(points) + batch_size - 1) // batch_size} OK")

    print(f"  Done: {len(points)} chunks indexed")
    return len(points)


def _build_qa_chunks(qa_pairs: list[dict], meta: dict, source_file: str) -> list[dict]:
    """Each Q&A pair becomes one chunk."""
    chunks = []
    for i, qa in enumerate(qa_pairs):
        q = qa.get("question", "").strip()
        a = qa.get("answer", "").strip()
        if not q and not a:
            continue
        search_text = f"{meta['company']} {meta['position']} {meta['round']} Q: {q} A: {a}"
        chunks.append({
            "chunk_id": f"qa-{i+1:04d}",
            "chunk_type": "qa_pair",
            "question": q,
            "answer": a,
            "search_text": search_text,
            "company": meta["company"],
            "position": meta["position"],
            "round": meta["round"],
            "date": meta["date"],
            "source_file": source_file,
        })
    return chunks


def _build_sw_chunks(raw_chunks: list[dict], meta: dict, source_file: str) -> list[dict]:
    """Sliding window chunks."""
    chunks = []
    for c in raw_chunks:
        chunks.append({
            "chunk_id": c["id"],
            "chunk_type": "sliding_window",
            "raw_text": c["text"],
            "search_text": c["text"][:500],
            "company": meta["company"],
            "position": meta["position"],
            "round": meta["round"],
            "date": meta["date"],
            "source_file": source_file,
        })
    return chunks


def init_collection():
    requests.delete(BASE)
    requests.put(BASE, json={
        "vectors": {"size": VECTOR_SIZE, "distance": DISTANCE_METRIC},
    })


def sync_index_file(file_path: str) -> int:
    """Sync index (no LLM, sliding window only). Used by upload API."""
    path = Path(file_path)
    name = path.name
    raw = path.read_bytes()
    text = extract_text(raw, name)
    chunks = sliding_window(text)
    sw = _build_sw_chunks(chunks, {}, name)

    texts = [c["search_text"] for c in sw]
    embeddings = embed_batch(texts)

    points = [{"id": i + 1, "vector": emb, "payload": c} for i, (c, emb) in enumerate(zip(sw, embeddings))]
    for i in range(0, len(points), 20):
        requests.put(f"{BASE}/points", json={"points": points[i:i+20]})
    return len(points)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m rag.indexer <file> [--preprocess]")
        sys.exit(1)

    file_path = sys.argv[1]
    use_llm = "--preprocess" in sys.argv

    # Read API key from .env for CLI
    from core.config import settings as s
    api_key = getattr(s, "deepseek_api_key", "") or ""

    init_collection()
    count = asyncio.run(index_file(file_path, api_key=api_key, use_llm=use_llm))
