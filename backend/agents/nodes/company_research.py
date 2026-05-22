"""Company research: query rewrite → Tavily search → LLM summary."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_llm
from agents.tools.tavily_search import tavily_search

REWRITE_PROMPT = """You are a search query optimizer. Rewrite the user's company name into an effective search query
for researching a company's interview process, tech stack, and culture.
Keep it concise — under 10 words.
Return JSON: {"query": "optimized search query"}"""

SUMMARY_PROMPT = """You are a career coach. Based on the search results below, write a structured company research report.
Use the same language as the company name (Chinese company → Chinese, English company → English).

Format your response as JSON:
{
  "company_overview": "Brief 2-3 sentence overview of the company",
  "tech_stack": ["Tech1", "Tech2", ...],
  "interview_style": "Description of interview format and what to expect",
  "culture": "Company culture highlights",
  "salary_range": "Known salary information if available, or 'Not publicly available'",
  "preparation_tips": "3-5 specific tips for interviewing at this company",
  "sources": ["url1", "url2"]
}"""


async def company_research(
    company_name: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "deepseek-chat",
    tavily_key: str = "",
) -> dict:
    """Run full company research pipeline. Uses user-provided LLM config."""
    llm = get_llm(temperature=0.2, api_key=api_key, base_url=base_url, model=model)

    # Step 1: Rewrite query
    rewrite_resp = await llm.ainvoke([
        SystemMessage(content=REWRITE_PROMPT),
        HumanMessage(content=company_name),
    ])
    try:
        content = rewrite_resp.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        query_data = json.loads(content.strip())
        search_query = query_data.get("query", company_name)
    except json.JSONDecodeError:
        search_query = f"{company_name} company interview process tech stack"

    # Step 2: Tavily search
    search_result = await tavily_search(search_query, api_key=tavily_key)

    if search_result.get("error"):
        return {
            "company_overview": f"Search failed: {search_result['error']}",
            "tech_stack": [],
            "interview_style": "N/A",
            "culture": "N/A",
            "salary_range": "N/A",
            "preparation_tips": "Try again later.",
            "sources": [],
            "error": search_result["error"],
        }

    # Step 3: Summarize search results
    search_text = "\n\n".join(
        f"Source {i+1}: {r.get('title','')}\n{r.get('content','')[:800]}"
        for i, r in enumerate(search_result.get("results", [])[:5])
    )

    summary_resp = await llm.ainvoke([
        SystemMessage(content=SUMMARY_PROMPT),
        HumanMessage(content=f"Company: {company_name}\n\nSearch Results:\n{search_text}"),
    ])

    try:
        content = summary_resp.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content.strip())
    except json.JSONDecodeError:
        result = {
            "company_overview": summary_resp.content[:500],
            "tech_stack": [],
            "interview_style": "Could not parse",
            "culture": "Could not parse",
            "salary_range": "N/A",
            "preparation_tips": "Check search results directly.",
        }

    result["sources"] = [r.get("url", "") for r in search_result.get("results", [])[:5]]
    return result
