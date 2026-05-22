"""User settings — LLM & search API configuration."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from core.crypto import decrypt_keys, encrypt_keys
from models.database import get_db
from models.user import User

router = APIRouter()


class LLMConfig(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class UserConfigRequest(BaseModel):
    llm: LLMConfig = LLMConfig()
    tavily_api_key: str | None = None


class UserConfigResponse(BaseModel):
    has_llm: bool = False
    llm_model: str = ""
    has_tavily: bool = False

    model_config = {"from_attributes": True}


@router.get("/config", response_model=UserConfigResponse)
async def get_config(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    keys = decrypt_keys(user.encrypted_api_keys)
    llm = keys.get("llm", {})
    return UserConfigResponse(
        has_llm=bool(llm.get("api_key")),
        llm_model=llm.get("model", ""),
        has_tavily=bool(keys.get("tavily_api_key")),
    )


@router.post("/config")
async def update_config(
    req: UserConfigRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    current = decrypt_keys(user.encrypted_api_keys)
    existing_llm = current.get("llm", {})

    if req.llm.api_key is not None:
        existing_llm["api_key"] = req.llm.api_key or existing_llm.get("api_key", "")
    if req.llm.base_url is not None:
        existing_llm["base_url"] = req.llm.base_url
    if req.llm.model is not None:
        existing_llm["model"] = req.llm.model or existing_llm.get("model", "deepseek-chat")

    if existing_llm.get("api_key"):  # Only save if there's at least a key
        current["llm"] = existing_llm
    if req.tavily_api_key is not None and req.tavily_api_key:
        current["tavily_api_key"] = req.tavily_api_key

    user.encrypted_api_keys = encrypt_keys(current)
    await db.commit()

    return {"status": "ok"}


async def get_user_keys(user_id: str, db: AsyncSession) -> dict:
    """Return decrypted keys for a user. Called by other routes."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {}
    return decrypt_keys(user.encrypted_api_keys)
