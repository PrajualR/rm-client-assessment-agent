from langgraph.graph import END, START, StateGraph

from src.agents.extraction_agent import extraction_agent
from src.agents.ingestion_agent import ingestion_agent
from src.agents.reconciliation_agent import reconciliation_agent
from src.agents.verification_agent import verification_agent
from src.graph.handlers import (
    auto_fill_handler,
    escalation_handler,
    human_review_handler,
)
from src.graph.state import AssessmentState


def route_after_ingestion(state):
    if state.get("ingestion_status") == "success":
        return "continue"

    return "human_review"


def route_after_extraction(state):
    if state.get("extraction_status") == "success":
        return "continue"

    return "human_review"


def route_after_verification(state):
    if state.get("verification_status") == "success":
        return "continue"

    return "human_review"


def route_after_reconciliation(state):
    final_route = state.get("final_route")

    if final_route == "AUTO_FILL":
        return "auto_fill"

    if final_route == "ESCALATE":
        return "escalate"

    return "human_review"


def build_graph():
    graph = StateGraph(AssessmentState)

    graph.add_node("ingestion", ingestion_agent)
    graph.add_node("extraction", extraction_agent)
    graph.add_node("verification", verification_agent)
    graph.add_node("reconciliation", reconciliation_agent)

    graph.add_node("auto_fill", auto_fill_handler)
    graph.add_node("escalate", escalation_handler)
    graph.add_node("human_review", human_review_handler)

    graph.add_edge(START, "ingestion")

    graph.add_conditional_edges(
        "ingestion",
        route_after_ingestion,
        {
            "continue": "extraction",
            "human_review": "human_review",
        },
    )

    graph.add_conditional_edges(
        "extraction",
        route_after_extraction,
        {
            "continue": "verification",
            "human_review": "human_review",
        },
    )

    graph.add_conditional_edges(
        "verification",
        route_after_verification,
        {
            "continue": "reconciliation",
            "human_review": "human_review",
        },
    )

    graph.add_conditional_edges(
        "reconciliation",
        route_after_reconciliation,
        {
            "auto_fill": "auto_fill",
            "escalate": "escalate",
            "human_review": "human_review",
        },
    )

    graph.add_edge("auto_fill", END)
    graph.add_edge("escalate", END)
    graph.add_edge("human_review", END)

    return graph.compile()