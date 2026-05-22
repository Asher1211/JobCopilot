"""Match analysis API with SSE streaming."""
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from agents.graph import agent_graph
from agents.state import AgentState
from api.middleware.auth import get_current_user
from api.routes.user import get_user_keys
from models.database import get_db

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".docx", ".pdf"}


def _sse(event: str, data: dict | str) -> ServerSentEvent:
    payload = data if isinstance(data, str) else json.dumps(data)
    return ServerSentEvent(event=event, data=payload)


async def _run_analysis(initial_state: AgentState):
    async for event in agent_graph.astream_events(initial_state, version="v2"):
        kind = event.get("event")

        if kind == "on_chain_start":
            name = event.get("name", "")
            if name in ("parse_resume", "match_analysis", "interview_prep", "optimize_resume"):
                yield _sse("node_start", {"node": name})

        elif kind == "on_chain_end":
            name = event.get("name", "")
            output = event.get("data", {}).get("output", {})
            if name == "match_analysis":
                if output.get("error"):
                    yield _sse("error", {"message": output["error"]})
                else:
                    resume_text = output.get("resume_text", "")
                    yield _sse("result", {
                        "match_score": output.get("match_score", 0),
                        "missing_skills": output.get("missing_skills", []),
                        "strengths": output.get("strengths", []),
                        "suggestions": output.get("suggestions", ""),
                        "route": output.get("route", ""),
                        "resume_text": resume_text[:3000],
                    })
            elif name in ("interview_prep", "optimize_resume"):
                no = output.get("node_output", {})
                yield _sse("result", {
                    "type": no.get("type", name),
                    "match_score": no.get("match_score", 0),
                    "advice": no.get("advice", ""),
                    "html": no.get("html", ""),
                    "changes_summary": no.get("changes_summary", ""),
                    "error": no.get("error", ""),
                    "exp_count": no.get("exp_count", 0),
                })
            elif name == "parse_resume":
                yield _sse("node_complete", {
                    "node": "parse_resume",
                    "resume_length": len(output.get("resume_text", "")),
                })

        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield _sse("stream", {"token": chunk.content})

        elif kind == "on_chain_error":
            error = event.get("data", {}).get("error", "Unknown error")
            yield _sse("error", {"message": str(error)})
            return

    yield _sse("done", "{}")


@router.post("/match")
async def match_analysis(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_keys = await get_user_keys(user_id, db)

    name = file.filename or "resume.docx"
    ext = name.lower()[name.rfind("."):]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Allowed: .docx, .pdf",
        )

    resume_bytes = await file.read()
    if len(resume_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)",
        )

    initial_state: AgentState = {
        "filename": name,
        "resume_bytes": resume_bytes,
        "jd_text": jd_text,
        "resume_text": "",
        "match_score": 0,
        "missing_skills": [],
        "strengths": [],
        "suggestions": "",
        "route": "",
        "user_api_keys": user_keys,
        "retrieved_questions": [],
        "node_output": {},
        "error": "",
    }

    return EventSourceResponse(_run_analysis(initial_state))
