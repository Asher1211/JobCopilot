from langgraph.graph import StateGraph, START, END

from agents.nodes.interview_prep import interview_prep_node
from agents.nodes.match_analysis import match_analysis_node
from agents.nodes.optimize_resume import optimize_resume_node
from agents.nodes.parse_resume import parse_resume_node
from agents.state import AgentState


def route_decision(state: AgentState) -> str:
    if state.get("error"):
        return END
    route = state.get("route", "")
    if route == "interview_prep":
        return "interview_prep"
    if route == "optimize_resume":
        return "optimize_resume"
    return END


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("parse_resume", parse_resume_node)
    graph.add_node("match_analysis", match_analysis_node)
    graph.add_node("interview_prep", interview_prep_node)
    graph.add_node("optimize_resume", optimize_resume_node)

    graph.add_edge(START, "parse_resume")
    graph.add_edge("parse_resume", "match_analysis")

    graph.add_conditional_edges(
        "match_analysis", route_decision,
        {"interview_prep": "interview_prep", "optimize_resume": "optimize_resume", END: END},
    )

    graph.add_edge("interview_prep", END)
    graph.add_edge("optimize_resume", END)

    return graph.compile()


agent_graph = build_graph()
