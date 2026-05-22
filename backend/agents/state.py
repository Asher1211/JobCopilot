from typing import Literal, TypedDict

Route = Literal["interview_prep", "optimize_resume", "error", ""]


class AgentState(TypedDict):
    # Input
    filename: str
    resume_bytes: bytes
    jd_text: str

    # Parsed
    resume_text: str

    # Match result
    match_score: int
    missing_skills: list[str]
    strengths: list[str]
    suggestions: str

    # Routing
    route: Route

    # RAG output —面经检索结果
    retrieved_experiences: list[dict]

    # Interview prep / Resume optimize output
    node_output: dict

    # User API keys (per-user, overrides server defaults)
    user_api_keys: dict

    # Error
    error: str
