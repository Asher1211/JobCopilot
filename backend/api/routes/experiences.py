"""Upload, list, delete & search interview experience chunks."""
import json
import asyncio
import os
import tempfile
import traceback

import requests
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from api.middleware.auth import get_current_user
from api.routes.user import get_user_keys
from core.config import settings
from models.database import get_db
from rag.chunker import extract_text, sliding_window
from rag.embedder import embed_batch
from rag.preprocessor import preprocess
from rag.retriever import retrieve

router = APIRouter()
ALLOWED_EXTENSIONS = {".docx", ".pdf", ".txt"}
MAX_SIZE = 20 * 1024 * 1024
BASE = f"{settings.qdrant_url}/collections/{settings.qdrant_collection}"


def _ensure_collection():
    r = requests.get(BASE)
    if r.status_code != 200:
        requests.put(BASE, json={"vectors": {"size": 512, "distance": "Cosine"}})


def _next_id() -> int:
    r = requests.get(BASE)
    if r.status_code == 200:
        return r.json()["result"].get("points_count", 0) + 1
    return 1


class SearchRequest(BaseModel):
    query: str = ""


def _build_points(chunks: list[dict], embeddings: list[list[float]], meta: dict, source_file: str) -> list[dict]:
    start = _next_id()
    points = []
    for i, (c, emb) in enumerate(zip(chunks, embeddings)):
        points.append({
            "id": start + i,
            "vector": emb,
            "payload": {
                "chunk_id": c.get("id", f"chunk-{i}"),
                "chunk_type": c.get("chunk_type", "sliding_window"),
                "question": c.get("question", ""),
                "answer": c.get("answer", ""),
                "raw_text": c.get("text", c.get("raw_text", "")),
                "search_text": c.get("search_text", c.get("text", ""))[:500],
                "company": meta.get("company", ""),
                "position": meta.get("position", ""),
                "round": meta.get("round", ""),
                "date": meta.get("date", ""),
                "source_file": source_file,
            },
        })
    return points


# ── Upload ──

@router.post("/upload")
async def upload_experience(
    file: UploadFile = File(...),
    mode: str = Query(default="sw"),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    name = file.filename or "experience.txt"
    ext = name.lower()[name.rfind("."):]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported: {ext}")

    raw = await file.read()
    if len(raw) > MAX_SIZE:
        raise HTTPException(413, "File too large (max 20MB)")

    try:
        text = extract_text(raw, name)
        meta = {"company": "", "position": "", "round": "", "date": ""}
        chunks: list[dict] = []

        if mode == "llm":
            keys = await get_user_keys(user_id, db)
            llm_cfg = keys.get("llm", {})
            api_key = llm_cfg.get("api_key", "")
            if api_key:
                result = await preprocess(text, api_key, llm_cfg.get("base_url", ""), llm_cfg.get("model", "deepseek-chat"))
                meta = {k: result.get(k, "") for k in ["company", "position", "round", "date"]}
                qa_pairs = result.get("qa_pairs", [])
                if qa_pairs:
                    chunks = [
                        {
                            "id": f"qa-{j+1:04d}", "chunk_type": "qa_pair",
                            "question": qa.get("question", ""), "answer": qa.get("answer", ""),
                            "search_text": f"{meta['company']} {meta['position']} {meta['round']} Q: {qa.get('question','')} A: {qa.get('answer','')}",
                        }
                        for j, qa in enumerate(qa_pairs)
                    ]

            if not chunks:
                sw = sliding_window(text)
                chunks = [{"id": c["id"], "chunk_type": "sliding_window", "text": c["text"], "search_text": c["text"][:500]} for c in sw]
        else:
            sw = sliding_window(text)
            chunks = [{"id": c["id"], "chunk_type": "sliding_window", "text": c["text"], "search_text": c["text"][:500]} for c in sw]

        search_texts = [c.get("search_text", c.get("text", ""))[:500] for c in chunks]
        embeddings = embed_batch(search_texts)

        _ensure_collection()
        points = _build_points(chunks, embeddings, meta, name)
        for i in range(0, len(points), 20):
            resp = requests.put(f"{BASE}/points", json={"points": points[i:i+20]})
            if resp.status_code != 200:
                raise Exception(f"Qdrant write error: {resp.status_code}")

        return {"status": "ok", "chunks": len(points), "mode": mode, "filename": name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Indexing failed: {str(e)[-300:]}")


# ── List ──

@router.get("/list")
async def list_chunks(user_id: str = Depends(get_current_user)):
    _ensure_collection()
    r = requests.post(f"{BASE}/points/scroll", json={"limit": 500, "with_payload": True, "with_vector": False})
    points = r.json().get("result", {}).get("points", [])
    return {
        "total": len(points),
        "chunks": [
            {"id": p["id"], **p.get("payload", {})}
            for p in points
        ],
    }


# ── Delete ──

@router.delete("/chunks/{chunk_id}")
async def delete_chunk(chunk_id: int, user_id: str = Depends(get_current_user)):
    r = requests.post(f"{BASE}/points/delete", json={"points": [chunk_id]})
    if r.status_code != 200:
        raise HTTPException(500, "Delete failed")
    return {"status": "deleted", "id": chunk_id}


# ── Search ──

@router.post("/search")
async def search_experiences(req: SearchRequest, user_id: str = Depends(get_current_user)):
    async def _stream():
        results = retrieve(query=req.query, limit=5)
        yield {"event": "result", "data": json.dumps({"results": results})}
        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(_stream())
