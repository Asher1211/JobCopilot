import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_llm
from agents.state import AgentState

ROUTE_INTERVIEW = "interview_prep"
ROUTE_OPTIMIZE = "optimize_resume"
MATCH_THRESHOLD = 60

MATCH_PROMPT = """You are a senior technical interviewer and career coach. Analyze the match between the following resume and job description (JD).

Evaluate across these dimensions:
1. Tech stack match
2. Project experience relevance
3. Education background fit
4. Overall competitiveness

Respond with valid JSON only (no markdown, no code fences):
{
  "match_score": <integer 0-100>,
  "missing_skills": ["skill1", "skill2"],
  "strengths": ["strength1", "strength2"],
  "suggestions": "Concise improvement advice covering skill gaps and resume wording, under 300 characters"
}

Use the same language as the resume text. If the resume is in Chinese, output Chinese.

Scoring:
- 90-100: Excellent match — all core skills met
- 70-89: Good match — most skills met, minor gaps
- 50-69: Partial match — noticeable skill gaps
- 30-49: Low match — significant gaps
- 0-29: Poor match — requirements barely met"""


async def match_analysis_node(state: AgentState) -> dict:
    resume = state.get("resume_text", "")
    jd = state.get("jd_text", "")

    if not resume:
        return {"error": "Resume parsing failed, cannot analyze", "route": "error"}
    if not jd:
        return {"error": "Please provide a job description", "route": "error"}

    keys = state.get("user_api_keys", {})
    llm_cfg = keys.get("llm", {})
    llm = get_llm(
        temperature=0.3,
        api_key=llm_cfg.get("api_key", ""),
        base_url=llm_cfg.get("base_url", ""),
        model=llm_cfg.get("model", "deepseek-chat"),
    )
    messages = [
        SystemMessage(content=MATCH_PROMPT),
        HumanMessage(content=f"## Resume\n\n{resume}\n\n## Job Description\n\n{jd}"),
    ]

    try:
        response = await llm.ainvoke(messages)
    except Exception as e:
        return {
            "match_score": 0,
            "missing_skills": [],
            "strengths": [],
            "suggestions": "",
            "route": "error",
            "error": f"LLM call failed: {e}",
        }

    try:
        content = response.content.strip()

        # Strip markdown code fences if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"): content = content[4:]
            content = content.strip()

        result = json.loads(content)
        match_score = int(result.get("match_score", 0))
        route = ROUTE_INTERVIEW if match_score >= MATCH_THRESHOLD else ROUTE_OPTIMIZE

        return {
            "match_score": match_score,
            "missing_skills": result.get("missing_skills", []),
            "strengths": result.get("strengths", []),
            "suggestions": result.get("suggestions", ""),
            "route": route,
            "resume_text": resume,
        }
    except json.JSONDecodeError:
        raw = response.content.strip()
        try:
            s = raw.find("{"); e = raw.rfind("}")
            if s >= 0 and e > s:
                result = json.loads(raw[s:e+1])
                match_score = int(result.get("match_score", 0))
                route = ROUTE_INTERVIEW if match_score >= MATCH_THRESHOLD else ROUTE_OPTIMIZE
                return {
                    "match_score": match_score,
                    "missing_skills": result.get("missing_skills", []),
                    "strengths": result.get("strengths", []),
                    "suggestions": result.get("suggestions", ""),
                    "route": route,
                    "resume_text": resume,
                }
            else:
                raise ValueError("No JSON object found")
        except:
            return {
                "match_score": 0, "missing_skills": [], "strengths": [], "suggestions": "",
                "route": "error", "error": f"JSON parse error. Raw: {raw[:300]}",
            }
