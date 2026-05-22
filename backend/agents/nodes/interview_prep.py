"""Interview prep node — search 面经库, feed to LLM for advice generation."""
from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_llm
from agents.state import AgentState
from rag.retriever import retrieve

ADVICE_PROMPT = """You are a career coach. Based on the candidate's analysis results and
relevant real interview experiences retrieved from a database, generate a concise preparation guide.
Use the same language as the resume text.

## Candidate Profile
- Match Score: {match_score}/100
- Strengths: {strengths}
- Missing Skills: {missing}
- Suggestions: {suggestions}

## Relevant Real Interview Experiences
{experiences}

## Instructions
Write a practical preparation guide (in English, 3-5 bullet points).
For each bullet:
1. Reference a specific real interview question or scenario from the experiences above (mention the company if available)
2. Give a concrete preparation tip

Keep it under 400 words. Use a direct, helpful tone."""


async def interview_prep_node(state: AgentState) -> dict:
    missing = state.get("missing_skills", [])
    strengths = state.get("strengths", [])
    suggestions = state.get("suggestions", "")
    jd_text = state.get("jd_text", "")
    user_keys = state.get("user_api_keys", {})
    llm_cfg = user_keys.get("llm", {})

    # Build search query from the analysis results
    query = " ".join(missing[:5] + strengths[:3])
    if not query.strip():
        query = jd_text[:500]

    # Retrieve relevant experiences
    try:
        raw_experiences = retrieve(query=query, limit=5)
    except Exception:
        raw_experiences = []

    # Format experiences as context for LLM
    exp_context_parts: list[str] = []
    for i, exp in enumerate(raw_experiences):
        meta = [exp.get("company"), exp.get("position"), exp.get("round")]
        meta_str = " · ".join(filter(bool, meta)) or "Unknown"
        content = exp.get("question") or exp.get("raw_text", exp.get("search_text", ""))
        exp_context_parts.append(f"[{i+1}] {meta_str}\n   {content[:300]}")

    exp_context = "\n\n".join(exp_context_parts) if exp_context_parts else "No relevant experiences found."

    # Generate advice with LLM
    try:
        llm = get_llm(
            temperature=0.3,
            api_key=llm_cfg.get("api_key", ""),
            base_url=llm_cfg.get("base_url", ""),
            model=llm_cfg.get("model", "deepseek-chat"),
        )
        prompt = ADVICE_PROMPT.format(
            match_score=state.get("match_score", 0),
            strengths=", ".join(strengths) if strengths else "N/A",
            missing=", ".join(missing) if missing else "N/A",
            suggestions=suggestions or "N/A",
            experiences=exp_context,
        )
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        advice = resp.content.strip()
    except Exception:
        advice = "Review the identified missing skills and practice related interview questions."

    return {
        "retrieved_experiences": raw_experiences,
        "node_output": {
            "type": "interview_prep",
            "match_score": state.get("match_score", 0),
            "advice": advice,
            "exp_count": len(raw_experiences),
        },
    }
