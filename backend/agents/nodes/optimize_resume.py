"""Resume optimization — LLM decides sections, outputs JSON, backend renders HTML."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_llm
from agents.state import AgentState

PROMPT = """You are a senior resume consultant. Optimize this resume for the target JD. Use the same language as the original resume.

Original Resume:
{resume}

Target JD:
{jd}

Match Score: {score}/100 | Strengths: {strengths} | Missing: {missing} | Suggestions: {suggestions}

Step 1 — Read the original resume. Identify all existing sections.

Step 2 — For EACH section, decide:
- KEEP: JD-relevant → rewrite it with JD-aligned wording, highlight transferable skills that cover missing skills
- REMOVE: irrelevant or weakens the application
- ADD: the JD requires something not in the resume → add it ONLY if candidate has transferable experience

Step 3 — For MISSING skills: rewrite the closest existing experience to demonstrate transferable/adjacent skills. De-emphasize strengths that don't matter for this JD.

Return ONLY valid JSON (no markdown, no code fences):
{{
  "name": "Full name",
  "title": "Professional headline optimized for JD",
  "decisions": "What was kept, removed, added and why. Under 250 chars.",
  "sections": [
    {{
      "type": "summary|skills|experience|projects|education|custom",
      "heading": "Section heading",
      "action": "keep|add",
      "content": "Section content as a single string. For skills: comma-separated. For experience: use + prefix for bullets, one per line."
    }}
  ]
}}

RULES:
- NEVER fabricate experience — every new claim must trace to original resume
- Prioritize closing the missing-skill gap by rewriting, not inventing
- De-emphasize or drop JD-irrelevant content
- Quantify achievements where possible
- Use JD keywords naturally"""

SECTION_HTML = {
    "summary":   '<div class="summary">{content}</div>',
    "skills":    '<h2>{heading}</h2><p class="skills">{content}</p>',
    "experience":'<h2>{heading}</h2>{items}',
    "projects":  '<h2>{heading}</h2>{items}',
    "education": '<h2>{heading}</h2><p class="education">{content}</p>',
    "certifications": '<h2>{heading}</h2><p class="education">{content}</p>',
    "languages": '<h2>{heading}</h2><p class="education">{content}</p>',
    "custom":    '<h2>{heading}</h2><p>{content}</p>',
}

HTML_WRAPPER = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Work Sans','Noto Sans SC','Segoe UI',sans-serif;font-size:13px;line-height:1.6;color:#000;max-width:800px;margin:0 auto;padding:40px 48px}}
h1{{font-family:'Archivo Black','Noto Sans SC',sans-serif;font-size:28px;font-weight:400;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px}}
h2{{font-family:'Archivo Black','Noto Sans SC',sans-serif;font-size:13px;font-weight:400;text-transform:uppercase;letter-spacing:.1em;border-bottom:2px solid #000;padding-bottom:4px;margin-top:28px;margin-bottom:12px}}
.subtitle{{font-size:15px;color:#444;margin-bottom:16px}}
.summary{{font-size:13px;line-height:1.7;margin-bottom:8px}}
.skills{{font-size:12px;color:#333}}
.exp-item{{margin-bottom:14px}}
.exp-header{{display:flex;justify-content:space-between;font-weight:600;font-size:13px}}
.exp-period{{font-family:'Space Mono',monospace;font-size:11px;color:#555}}
.exp-bullets{{list-style:none;padding-left:0;margin-top:4px}}
.exp-bullets li{{position:relative;padding-left:14px;margin-bottom:3px;font-size:12.5px}}
.exp-bullets li::before{{content:'+';position:absolute;left:0;color:#000;font-weight:bold}}
.education{{font-size:13px}}
.decisions{{font-size:10px;color:#999;border-top:1px solid #ddd;margin-top:32px;padding-top:8px;font-family:'Space Mono',monospace}}
@media print{{body{{padding:30px 36px}}}}
</style></head><body>
<h1>{name}</h1><div class="subtitle">{title}</div>
{sections}
<div class="decisions">{decisions}</div>
</body></html>"""


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if "```json" in raw:
        inner = raw.split("```json",1)[1].split("```",1)[0].strip()
        return json.loads(inner)
    if "```" in raw:
        inner = raw.split("```",1)[1].strip()
        if inner.startswith("json"): inner = inner[4:]
        return json.loads(inner.strip())
    s = raw.find("{")
    e = raw.rfind("}")
    if s >= 0 and e > s:
        return json.loads(raw[s:e+1])
    return json.loads(raw)


def _to_str(val) -> str:
    if isinstance(val, list): return ", ".join(str(v) for v in val)
    if isinstance(val, str):
        try:
            p = json.loads(val)
            if isinstance(p, list): return ", ".join(str(v) for v in p)
        except: pass
    return str(val)


def _render_section(sec: dict) -> str:
    stype = sec.get("type","custom")
    heading = sec.get("heading","")
    content = sec.get("content","")
    if sec.get("action") == "remove":
        return ""

    if stype in ("experience","projects"):
        # Parse plain text: lines starting with + are bullets, other lines are headers
        lines = content.strip().split("\n") if isinstance(content,str) else []
        bullets = []
        headers = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("+"):
                bullets.append(stripped[1:].strip())
            elif stripped:
                headers.append(stripped)
        b_html = "".join(f"<li>{x}</li>" for x in bullets)
        h_html = "".join(f'<div class="exp-item"><div class="exp-header"><span>{h}</span></div></div>' for h in headers)
        return SECTION_HTML[stype].format(heading=heading, items=h_html + f'<ul class="exp-bullets">{b_html}</ul>' if bullets else h_html)

    tpl = SECTION_HTML.get(stype, SECTION_HTML["custom"])
    return tpl.format(heading=heading, content=_to_str(content))


async def optimize_resume_node(state: AgentState) -> dict:
    resume = state.get("resume_text","")
    jd = state.get("jd_text","")
    user_keys = state.get("user_api_keys",{})
    llm_cfg = user_keys.get("llm",{})

    if not resume or not jd:
        return {"node_output":{"type":"optimize_resume","error":"Missing resume or JD"},"retrieved_experiences":[]}

    try:
        llm = get_llm(temperature=0.3, api_key=llm_cfg.get("api_key",""), base_url=llm_cfg.get("base_url",""), model=llm_cfg.get("model","deepseek-chat"))
        prompt = PROMPT.format(resume=resume, jd=jd, score=state.get("match_score",0),
            strengths=", ".join(state.get("strengths",[])),
            missing=", ".join(state.get("missing_skills",[])),
            suggestions=state.get("suggestions",""))
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        data = _parse_json(resp.content.strip())
        sections_html = "\n".join(_render_section(s) for s in data.get("sections",[]))
        html = HTML_WRAPPER.format(
            name=data.get("name","Your Name"),
            title=data.get("title",""),
            sections=sections_html,
            decisions=data.get("decisions",""),
        )
    except Exception as e:
        return {"node_output":{"type":"optimize_resume","error":str(e)[:300]},"retrieved_experiences":[]}

    return {
        "node_output":{"type":"optimize_resume","html":html,"changes_summary":data.get("decisions",""),"message":"Resume optimized."},
        "retrieved_experiences":[],
    }
