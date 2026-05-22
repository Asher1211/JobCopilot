"""Mock interview API with layered memory management."""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from agents.nodes.mock_interview import evaluate_answer, generate_first_question
from api.middleware.auth import get_current_user
from api.routes.user import get_user_keys
from memory.manager import (
    InterviewMemory,
    add_turn,
    create_memory,
    from_dict,
    to_dict,
)
from models.database import get_db
from models.interview import InterviewSession
from models.user import User

router = APIRouter()


class StartRequest(BaseModel):
    jd_text: str = ""
    resume_text: str = ""
    role: str = "software engineering"
    match_score: int = 0
    strengths: list[str] = []
    missing_skills: list[str] = []


class ChatRequest(BaseModel):
    answer: str


async def _sse_event(event: str, data: dict):
    return {"event": event, "data": json.dumps(data)}


@router.post("/start")
async def start_interview(
    req: StartRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Fetch user's resume if not provided
    resume_text = req.resume_text
    if not resume_text:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user and user.resume_text:
            resume_text = user.resume_text

    async def _stream():
        memory = create_memory()

        keys = await get_user_keys(user_id, db)
        llm = keys.get("llm", {})

        yield {"event": "status", "data": json.dumps({"status": "generating_question"})}

        first = await generate_first_question(
            resume_text, req.jd_text, req.role,
            match_score=req.match_score,
            strengths=req.strengths,
            missing_skills=req.missing_skills,
            api_key=llm.get("api_key", ""),
            base_url=llm.get("base_url", ""),
            model=llm.get("model", "deepseek-chat"),
        )

        if first.get("question"):
            add_turn(memory, "interviewer", first["question"])

        # Persist session
        session = InterviewSession(
            user_id=user_id,
            jd_text=req.jd_text[:5000],
            resume_text=resume_text[:5000],
            match_score=req.match_score,
            short_term_memory=json.dumps(to_dict(memory).get("short_term", [])),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        yield {"event": "started", "data": json.dumps({
            "session_id": str(session.id),
            "question": first.get("question", ""),
            "topic": first.get("topic", ""),
            "difficulty": first.get("difficulty", ""),
        })}

    return EventSourceResponse(_stream())


@router.post("/chat/{session_id}")
async def chat(
    session_id: str,
    req: ChatRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Load session
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id),
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Not your session")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session already ended")

    # Rebuild memory
    memory = InterviewMemory()
    if session.short_term_memory:
        try:
            data = json.loads(session.short_term_memory)
            memory = from_dict({
                "short_term": data,
                "long_term_summary": session.long_term_summary or "",
                "structured": json.loads(session.structured_info) if session.structured_info else {},
            })
        except json.JSONDecodeError:
            pass

    async def _stream():
        nonlocal memory

        keys = await get_user_keys(user_id, db)
        llm = keys.get("llm", {})

        yield {"event": "status", "data": json.dumps({"status": "evaluating"})}

        result_eval = await evaluate_answer(
            memory, req.answer,
            jd_text=session.jd_text or "",
            match_score=session.match_score or 0,
            api_key=llm.get("api_key", ""),
            base_url=llm.get("base_url", ""),
            model=llm.get("model", "deepseek-chat"),
        )

        # Persist updated memory
        mem_dict = to_dict(memory)
        session.short_term_memory = json.dumps(mem_dict.get("short_term", []))
        session.long_term_summary = mem_dict.get("long_term_summary", "")
        session.structured_info = json.dumps(mem_dict.get("structured", {}))
        if result_eval.get("next_question") == "END":
            session.status = "completed"
        await db.commit()

        yield {"event": "feedback", "data": json.dumps(result_eval)}

        if result_eval.get("next_question") == "END":
            yield {"event": "done", "data": "{}"}

    return EventSourceResponse(_stream())
