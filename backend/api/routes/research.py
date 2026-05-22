"""Company research API with SSE streaming."""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from agents.nodes.company_research import company_research
from api.middleware.auth import get_current_user
from api.routes.user import get_user_keys
from models.database import get_db

router = APIRouter()


class ResearchRequest(BaseModel):
    company_name: str


async def _run_research(
    company_name: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "deepseek-chat",
    tavily_key: str = "",
):
    yield {"event": "node_start", "data": json.dumps({"node": "query_rewrite"})}
    yield {"event": "node_start", "data": json.dumps({"node": "tavily_search"})}
    yield {"event": "node_start", "data": json.dumps({"node": "summarize"})}

    result = await company_research(
        company_name,
        api_key=api_key,
        base_url=base_url,
        model=model,
        tavily_key=tavily_key,
    )

    yield {"event": "result", "data": json.dumps(result)}
    yield {"event": "done", "data": "{}"}


@router.post("/search")
async def search(
    req: ResearchRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    keys = await get_user_keys(user_id, db)
    llm = keys.get("llm", {})
    return EventSourceResponse(_run_research(
        req.company_name,
        api_key=llm.get("api_key", ""),
        base_url=llm.get("base_url", ""),
        model=llm.get("model", "deepseek-chat"),
        tavily_key=keys.get("tavily_api_key", ""),
    ))
