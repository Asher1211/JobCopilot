"""Layered memory manager for interview sessions."""
import json
from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str  # "interviewer" | "candidate"
    content: str


@dataclass
class InterviewMemory:
    short_term: list[Turn] = field(default_factory=list)  # Last 3 turns verbatim
    long_term_summary: str = ""  # LLM summary of older turns
    structured: dict = field(default_factory=dict)  # Key entities: {projects, skills, experience}

    MAX_SHORT_TERM = 3  # pcs of turns


def create_memory() -> InterviewMemory:
    return InterviewMemory()


def add_turn(memory: InterviewMemory, role: str, content: str) -> None:
    memory.short_term.append(Turn(role=role, content=content))

    if len(memory.short_term) > memory.MAX_SHORT_TERM * 2:
        # Move oldest turns to summary
        overflow = memory.short_term[: -memory.MAX_SHORT_TERM * 2]
        memory.short_term = memory.short_term[-memory.MAX_SHORT_TERM * 2:]
        overflow_text = "\n".join(f"{t.role}: {t.content}" for t in overflow)
        memory.long_term_summary = (
            f"{memory.long_term_summary}\n[Earlier]\n{overflow_text}"
        )[:2000]


def update_structured(memory: InterviewMemory, entities: dict) -> None:
    memory.structured.update(entities)


def build_context(memory: InterviewMemory) -> str:
    parts: list[str] = []

    if memory.structured:
        parts.append("### Candidate Profile\n" + json.dumps(memory.structured, indent=2))

    if memory.long_term_summary:
        parts.append("### Earlier Conversation\n" + memory.long_term_summary)

    if memory.short_term:
        parts.append(
            "### Recent Conversation\n"
            + "\n".join(f"{t.role.capitalize()}: {t.content}" for t in memory.short_term),
        )

    return "\n\n".join(parts)


def to_dict(memory: InterviewMemory) -> dict:
    return {
        "short_term": [{"role": t.role, "content": t.content} for t in memory.short_term],
        "long_term_summary": memory.long_term_summary,
        "structured": memory.structured,
    }


def from_dict(data: dict) -> InterviewMemory:
    return InterviewMemory(
        short_term=[Turn(**t) for t in data.get("short_term", [])],
        long_term_summary=data.get("long_term_summary", ""),
        structured=data.get("structured", {}),
    )
