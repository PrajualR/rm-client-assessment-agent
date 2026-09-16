from src.agents import verification_agent
from src.graph.workflow import build_graph


VALID_DOCUMENT = """
Client Name: ABC Technologies
Country of Incorporation: India
Business Activity: Information Technology Services
Annual Revenue: 10000000
Existing Bank Relationship: Yes
"""


def create_initial_state(document_text: str) -> dict:
    return {
        "case_id": "TEST-001",
        "document_text": document_text,
        "questions": [
            {
                "question_id": "Q1",
                "question": "What is the client's country of incorporation?",
                "field_name": "country_of_incorporation",
            },
            {
                "question_id": "Q2",
                "question": "What is the client's business activity?",
                "field_name": "business_activity",
            },
            {
                "question_id": "Q3",
                "question": "What is the client's annual revenue?",
                "field_name": "annual_revenue",
            },
            {
                "question_id": "Q4",
                "question": "Does the client have an existing bank relationship?",
                "field_name": "existing_bank_relationship",
            },
        ],
        "ingestion_status": "",
        "extraction_status": "",
        "verification_status": "",
        "reconciliation_status": "",
        "workflow_status": "",
        "extracted_data": {},
        "verification_results": {},
        "reconciliation_results": {},
        "question_results": {},
        "final_route": "",
        "errors": [],
        "audit_log": [],
    }


def invoke_workflow(document_text: str) -> dict:
    graph = build_graph()
    initial_state = create_initial_state(document_text)

    return graph.invoke(initial_state)


def force_all_fields_auto_fill(monkeypatch):
    """
    Make all fields pass verification with high confidence.

    This is used only for tests that focus on the successful
    auto-fill or single-field routing behavior.
    """

    def fake_verify_field(field_name, value):
        return {
            "field_name": field_name,
            "value": value,
            "verification_status": "PASSED",
            "confidence": 0.95,
            "reason": "Test verification passed with high confidence.",
        }

    monkeypatch.setattr(
        verification_agent,
        "verify_field",
        fake_verify_field,
    )


def force_one_field_confidence(monkeypatch, target_field, confidence):
    """
    Make all fields pass with high confidence except one selected field.
    """

    def fake_verify_field(field_name, value):
        if field_name == target_field:
            verification_status = (
                "PASSED" if confidence >= 0.60 else "REVIEW_REQUIRED"
            )

            return {
                "field_name": field_name,
                "value": value,
                "verification_status": verification_status,
                "confidence": confidence,
                "reason": "Confidence intentionally changed for testing.",
            }

        return {
            "field_name": field_name,
            "value": value,
            "verification_status": "PASSED",
            "confidence": 0.95,
            "reason": "Test verification passed with high confidence.",
        }

    monkeypatch.setattr(
        verification_agent,
        "verify_field",
        fake_verify_field,
    )


def test_successful_auto_fill_flow(monkeypatch):
    force_all_fields_auto_fill(monkeypatch)

    result = invoke_workflow(VALID_DOCUMENT)

    assert result["workflow_status"] == "AUTO_FILL_READY"
    assert result["final_route"] == "AUTO_FILL"
    assert result["errors"] == []

    assert result["ingestion_status"] == "success"
    assert result["extraction_status"] == "success"
    assert result["verification_status"] == "success"
    assert result["reconciliation_status"] == "success"

    assert len(result["question_results"]) == 4
    assert len(result["reconciliation_results"]) == 4

    for reconciliation_result in result[
        "reconciliation_results"
    ].values():
        assert reconciliation_result["route"] == "AUTO_FILL"


def test_escalation_flow(monkeypatch):
    force_one_field_confidence(
        monkeypatch,
        target_field="business_activity",
        confidence=0.70,
    )

    result = invoke_workflow(VALID_DOCUMENT)

    assert result["workflow_status"] == "ESCALATION_REQUIRED"
    assert result["final_route"] == "ESCALATE"

    business_activity_result = result["reconciliation_results"]["Q2"]

    assert business_activity_result["route"] == "ESCALATE"
    assert business_activity_result["confidence"] == 0.70

    assert result["reconciliation_results"]["Q1"]["route"] == "AUTO_FILL"
    assert result["reconciliation_results"]["Q3"]["route"] == "AUTO_FILL"
    assert result["reconciliation_results"]["Q4"]["route"] == "AUTO_FILL"


def test_human_review_flow(monkeypatch):
    force_one_field_confidence(
        monkeypatch,
        target_field="annual_revenue",
        confidence=0.40,
    )

    result = invoke_workflow(VALID_DOCUMENT)

    assert result["workflow_status"] == "HUMAN_REVIEW_REQUIRED"
    assert result["final_route"] == "HUMAN_REVIEW"

    annual_revenue_result = result["reconciliation_results"]["Q3"]

    assert annual_revenue_result["route"] == "HUMAN_REVIEW"
    assert annual_revenue_result["confidence"] == 0.40

    assert result["reconciliation_results"]["Q1"]["route"] == "AUTO_FILL"
    assert result["reconciliation_results"]["Q2"]["route"] == "AUTO_FILL"
    assert result["reconciliation_results"]["Q4"]["route"] == "AUTO_FILL"


def test_missing_document_value():
    """
    Do not monkeypatch verification here.

    The real verification logic must identify the missing annual
    revenue and route the question to HUMAN_REVIEW.
    """

    document_without_revenue = """
    Client Name: ABC Technologies
    Country of Incorporation: India
    Business Activity: Information Technology Services
    Existing Bank Relationship: Yes
    """

    result = invoke_workflow(document_without_revenue)

    annual_revenue_result = result["question_results"]["Q3"]

    assert annual_revenue_result["extracted_value"] is None
    assert annual_revenue_result["extraction_status"] == "MISSING"

    assert result["final_route"] == "HUMAN_REVIEW"
    assert result["workflow_status"] == "HUMAN_REVIEW_REQUIRED"

    assert result["reconciliation_results"]["Q3"]["route"] == "HUMAN_REVIEW"


def test_invalid_field_value():
    invalid_document = """
    Client Name: ABC Technologies
    Country of Incorporation: Mars
    Business Activity: Information Technology Services
    Annual Revenue: 10000000
    Existing Bank Relationship: Yes
    """

    result = invoke_workflow(invalid_document)

    country_result = result["question_results"]["Q1"]

    assert country_result["verification_status"] == "FAILED"
    assert country_result["final_route"] == "HUMAN_REVIEW"

    assert result["final_route"] == "HUMAN_REVIEW"
    assert result["workflow_status"] == "HUMAN_REVIEW_REQUIRED"


def test_ingestion_failure():
    result = invoke_workflow("")

    assert result["ingestion_status"] == "failed"
    assert result["final_route"] == "HUMAN_REVIEW"
    assert result["workflow_status"] == "HUMAN_REVIEW_REQUIRED"

    assert len(result["errors"]) > 0