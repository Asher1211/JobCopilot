"""Mock interview logic: question generation, answer evaluation."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_llm
from memory.manager import (
    InterviewMemory,
    add_turn,
    build_context,
    create_memory,
    update_structured,
)

FIRST_QUESTION_PROMPT = """You are an expert technical interviewer for {role} positions.

The candidate's resume has been analyzed against the job description.
Match score: {match_score}/100. This is YOUR internal reference — do NOT mention the score to the candidate.

Your behavior based on the score:
- Score < 50: The candidate has significant gaps. Start with a warm, encouraging opening. Briefly acknowledge the gap areas and offer a concrete tip before asking the first question. Focus on foundational concepts they SHOULD know.
- Score 50-70: Moderate match. Start with a neutral professional tone. Pick a skill they're strong at as a warm-up question, then prepare to probe weak areas in follow-ups.
- Score > 70: Strong match. Jump confidently into a deeper question about their project experience. Challenge them on architecture decisions and trade-offs.

Candidate Resume:
{resume}

Job Description:
{jd}

Strengths: {strengths}
Missing Skills: {missing}

IMPORTANT: Use the same language as the resume. Never say the match score out loud.
Respond with JSON:
{{
  "question": "Your opening message + first question (include encouragement/advice if score is low)",
  "topic": "What this question assesses",
  "difficulty": "easy|medium|hard"
}}"""

FEEDBACK_PROMPT = """You are an expert technical interviewer conducting an interview for the following job:

{job_description}

The candidate's resume was analyzed against this JD with a match score of {match_score}/100.
Use the same language as the resume. DO NOT mention the match score to the candidate.
Use the score only to calibrate your expectations and feedback tone.

Conversation so far:
{context}

The candidate just answered: "{answer}"

Respond with JSON:
{{
  "feedback": "Brief evaluation of the answer (strengths, areas to improve, 2-3 sentences)",
  "score": <integer 1-10>,
  "next_question": "The next interview question",
  "topic": "What the next question assesses",
  "entities": {{"key": "value"}}
}}

Rules:
- Balance your questions across 3 sources: the JD requirements, the candidate's resume projects, and the conversation context
- When the candidate mentions a project or tech they used, dig deeper into THEIR actual experience: "How did you handle X in that project?", "What was the hardest part of building Y?"
- Use the JD as a guide for WHAT skills matter, not as a question bank — only ask about JD skills if they naturally connect to what the candidate has done
- Prioritize depth over breadth: follow up on the current topic rather than jumping to a new JD bullet point
- If match score < 50: be encouraging, give constructive hints with questions, focus on fundamentals they should know
- If match score 50-70: balanced approach, start from strengths then probe weak areas
- If match score > 70: challenge deeper, ask about trade-offs, architecture decisions, and edge cases
- Use "entities" to extract and store important info from the answer
- After ~8-10 questions, set next_question to "END"
- If the answer is off-topic or shallow, give constructive feedback and steer back"""


async def generate_first_question(
    resume_text: str,
    jd_text: str,
    role: str = "software engineering",
    match_score: int = 0,
    strengths: list[str] | None = None,
    missing_skills: list[str] | None = None,
    api_key: str = "",
    base_url: str = "",
    model: str = "deepseek-chat",
) -> dict:
    llm = get_llm(temperature=0.7, api_key=api_key, base_url=base_url, model=model)
    prompt = FIRST_QUESTION_PROMPT.format(
        role=role,
        resume=resume_text[:2000],
        jd=jd_text[:1500],
        match_score=match_score,
        strengths=", ".join(strengths or []),
        missing=", ".join(missing_skills or []),
    )
    resp = await llm.ainvoke([HumanMessage(content=prompt)])
    return _parse_json(resp.content)


async def evaluate_answer(
    memory: InterviewMemory,
    answer: str,
    jd_text: str = "",
    match_score: int = 0,
    api_key: str = "",
    base_url: str = "",
    model: str = "deepseek-chat",
) -> dict:
    llm = get_llm(temperature=0.5, api_key=api_key, base_url=base_url, model=model)
    context = build_context(memory)
    prompt = FEEDBACK_PROMPT.format(
        match_score=match_score,
        job_description=jd_text[:1500] or "Software engineering position",
        context=context or "First question.",
        answer=answer,
    )
    resp = await llm.ainvoke([HumanMessage(content=prompt)])
    result = _parse_json(resp.content)

    # Update memory
    add_turn(memory, "candidate", answer)
    if result.get("next_question") and result["next_question"] != "END":
        add_turn(memory, "interviewer", result["next_question"])

    entities = result.pop("entities", {})
    if entities:
        update_structured(memory, entities)

    return result


def _parse_json(content: str) -> dict:
    try:
        text = content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"feedback": content[:300], "score": 0, "next_question": "Could you elaborate?", "topic": "general"}
