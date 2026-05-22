"""LLM-based metadata extraction from interview experience chunks."""
import json

from agents.llm import get_llm

EXTRACT_PROMPT = """Extract structured metadata from this interview experience chunk.
Return ONLY valid JSON (no markdown, no code fences):

{
  "company": "Company name, or empty string",
  "position": "Job position, or empty string",
  "interview_round": "一面/二面/三面/终面/HR面, or empty",
  "questions_asked": ["question 1", "question 2"],
  "difficulty": "easy/medium/hard",
  "key_takeaways": "What the candidate learned, under 200 chars",
  "interview_result": "pass/fail/unknown"
}"""


async def extract_metadata(
    chunk_text: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "deepseek-chat",
) -> dict:
    if not api_key:
        return _empty_meta()

    try:
        llm = get_llm(temperature=0, api_key=api_key, base_url=base_url, model=model)
        resp = await llm.ainvoke(
            f"{EXTRACT_PROMPT}\n\n## Chunk\n{chunk_text[:3000]}"
        )
        content = resp.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception:
        return _empty_meta()


def _empty_meta() -> dict:
    return {
        "company": "",
        "position": "",
        "interview_round": "",
        "questions_asked": [],
        "difficulty": "medium",
        "key_takeaways": "",
        "interview_result": "unknown",
    }
