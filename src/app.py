import json
from pathlib import Path

from data.mock_questionnaire import questions
from src.config.settings import settings
from src.graph.workflow import build_graph
from src.services.assessment_response import (
    build_assessment_response,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
GRAPH_DIR = PROJECT_ROOT / "src" / "graph"
OUTPUT_DIR = PROJECT_ROOT / "output"


def main():
    graph = build_graph()

    print("Assessment configuration loaded.")
    print("Auto-fill threshold:", settings.auto_fill_threshold)
    print("Escalation threshold:", settings.escalation_threshold)

    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    png_data = graph.get_graph().draw_mermaid_png()
    graph_image_path = GRAPH_DIR / "assessment_graph.png"

    with open(graph_image_path, "wb") as file:
        file.write(png_data)

    print(f"Graph image saved to {graph_image_path}")

    document_path = DATA_DIR / "mock_document.txt"

    with open(document_path, "r", encoding="utf-8") as file:
        document_text = file.read()

    initial_state = {
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

    result = graph.invoke(initial_state)

    response = build_assessment_response(result)

    output_path = OUTPUT_DIR / "assessment_result.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            response.model_dump(mode="json"),
            file,
            indent=4,
        )

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
    print("JSON response saved to:", output_path)


if __name__ == "__main__":
    main()