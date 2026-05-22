from agents.state import AgentState
from parsers import parse_resume


async def parse_resume_node(state: AgentState) -> dict:
    try:
        text = await parse_resume(state["resume_bytes"], state["filename"])
        return {"resume_text": text}
    except Exception as e:
        return {"error": f"Document parsing failed: {e}"}
