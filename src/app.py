import json
from pathlib import Path

from data.mock_questionnaire import questions
from src.config.settings import settings
from src.graph.workflow import build_graph
from src.services.assessment_response import build_assessment_response

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
GRAPH_DIR = PROJECT_ROOT / "src" / "graph"
OUTPUT_DIR = PROJECT_ROOT / "output"


def save_graph_diagram(graph) -> None:
    """
    Generate and save the LangGraph diagram.

    Mermaid rendering may require an external service or network
    access. If rendering fails, the assessment workflow continues.
    """
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)

    graph_image_path = GRAPH_DIR / "assessment_graph.png"

    try:
        png_data = graph.get_graph().draw_mermaid_png()
        graph_image_path.write_bytes(png_data)

        print(f"Graph image saved to {graph_image_path}")

    except Exception as error:
        print("Graph image could not be generated.")
        print(f"Reason: {error}")
        print("Continuing without the graph image.")


def load_document() -> str:
    """
    Load the mock assessment document.
    """
    document_path = DATA_DIR / "mock_document.txt"

    with document_path.open("r", encoding="utf-8") as file:
        return file.read()


def build_initial_state(document_text: str) -> dict:
    """
    Build the initial LangGraph state for the assessment case.
    """
    return {
        "case_id": "CASE-001",
        "document_text": document_text,
        "questions": questions,
        "ingestion_status": "",
        "extraction_status": "",
        "verification_status": "",
        "reconciliation_status": "",
        "workflow_status": "started",
        "extracted_data": {},
        "verification_results": {},
        "reconciliation_results": {},
        "question_results": {},
        "final_route": "",
        "errors": [],
        "audit_log": [],
    }


def save_assessment_response(response) -> Path:
    """
    Save the final assessment response as JSON.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / "assessment_result.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            response.model_dump(mode="json"),
            file,
            indent=4,
        )

    return output_path


def print_assessment_summary(response) -> None:
    """
    Print the final assessment summary to the console.
    """
    print("\nAssessment completed.")
    print("Case ID:", response.case_id)
    print("Workflow status:", response.workflow_status)
    print("Final route:", response.final_route)

    print("\nSummary:")
    print("Total questions:", response.summary.total_questions)
    print("Answered:", response.summary.answered_count)
    print("Missing:", response.summary.missing_count)
    print("Auto-fill:", response.summary.auto_fill_count)
    print("Escalation:", response.summary.escalation_count)
    print("Human review:", response.summary.human_review_count)

    print("\nQuestion results:")

    for question in response.question_results:
        print(
            f"{question.question_id} -> "
            f"{question.field_name} | "
            f"Value: {question.final_value} | "
            f"Route: {question.final_route} | "
            f"Confidence: {question.final_confidence}"
        )

    print("\nAudit entries:", len(response.audit_log))


def main():
    graph = build_graph()

    print("Assessment configuration loaded.")
    print("Auto-fill threshold:", settings.auto_fill_threshold)
    print("Escalation threshold:", settings.escalation_threshold)

    # Mermaid is only used for visualization.
    # Failure here must not stop the actual workflow.
    save_graph_diagram(graph)

    document_text = load_document()
    initial_state = build_initial_state(document_text)

    result = graph.invoke(initial_state)

    response = build_assessment_response(result)

    output_path = save_assessment_response(response)

    print_assessment_summary(response)

    print("JSON response saved to:", output_path)


if __name__ == "__main__":
    main()
