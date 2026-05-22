"""LLM preprocessing: extract structured Q&A pairs from messy interview text.

If Q&A pairs can be extracted → one chunk per pair.
If not → caller falls back to sliding-window chunking.
"""

import json

from agents.llm import get_llm

EXTRACT_PROMPT = """You are processing a raw interview experience text. It may contain chat logs, typos, mixed languages.

Extract ALL question-answer pairs from this interview, plus metadata.

Return ONLY valid JSON (no markdown, no code fences):

{
  "company": "公司名 or empty",
  "position": "岗位名 or empty",
  "round": "一面/二面/三面/终面/HR面 or empty",
  "date": "YYYY-MM or empty",
  "qa_pairs": [
    {
      "question": "interviewer question (keep original language)",
      "answer": "candidate answer / interviewer feedback / result (keep original language, under 800 chars)"
    }
  ]
}

Rules:
- Each Q&A pair is ONE question + its answer/feedback
- If the text mentions a question but no answer, still include it with answer=""
- Keep original language (Chinese stays Chinese)
- If there are NO clear Q&A pairs, return empty qa_pairs array
- Respond with ONLY valid JSON"""


async def preprocess(
    text: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "deepseek-chat",
) -> dict:
    """Return {company, position, round, date, qa_pairs: [{question, answer}]}."""
    if not api_key or not text.strip():
        return {"company": "", "position": "", "round": "", "date": "", "qa_pairs": []}

    try:
        llm = get_llm(temperature=0.1, api_key=api_key, base_url=base_url, model=model)
        resp = await llm.ainvoke(f"{EXTRACT_PROMPT}\n\n## Raw Text\n{text[:6000]}")
        content = resp.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception:
        return {"company": "", "position": "", "round": "", "date": "", "qa_pairs": []}
