"""Interview session model."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    jd_text: Mapped[str | None] = mapped_column(Text)
    resume_text: Mapped[str | None] = mapped_column(Text)
    match_score: Mapped[int] = mapped_column(default=0)
    short_term_memory: Mapped[str | None] = mapped_column(Text)  # JSON: last 3 turns
    long_term_summary: Mapped[str | None] = mapped_column(Text)  # Summarized older turns
    structured_info: Mapped[str | None] = mapped_column(Text)  # JSON: key entities
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
