from typing import TypedDict


class AssessmentState(TypedDict):
    case_id: str
    document_text: str
    questions: list

    ingestion_status: str
    extraction_status: str
    verification_status: str
    reconciliation_status: str
    workflow_status: str

    extracted_data: dict
    verification_results: dict
    reconciliation_results: dict
    question_results: dict

    final_route: str
    errors: list
    audit_log: list
