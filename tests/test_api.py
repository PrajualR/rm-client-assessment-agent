from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["application"] == "Client Assessment Agent API"
    assert data["status"] == "running"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_assessment_with_complete_document():
    payload = {
        "case_id": "TEST-001",
        "document_text": (
            "Country of Incorporation: India\n"
            "Business Activity: Information Technology Services\n"
            "Annual Revenue: 10000000\n"
            "Existing Bank Relationship: Yes"
        ),
    }

    response = client.post(
        "/assessments",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == "TEST-001"
    assert data["workflow_status"] == "AUTO_FILL_READY"
    assert data["final_route"] == "AUTO_FILL"

    assert data["summary"]["total_questions"] == 4
    assert data["summary"]["auto_fill_count"] == 4
    assert data["summary"]["escalation_count"] == 0
    assert data["summary"]["human_review_count"] == 0
    assert data["summary"]["answered_count"] == 4
    assert data["summary"]["missing_count"] == 0

    assert data["errors"] == []
    assert len(data["question_results"]) == 4
    assert len(data["audit_log"]) >= 5


def test_create_assessment_with_missing_answer():
    payload = {
        "case_id": "TEST-002",
        "document_text": (
            "Country of Incorporation: India\n"
            "Business Activity: Information Technology Services\n"
            "Existing Bank Relationship: Yes"
        ),
    }

    response = client.post(
        "/assessments",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == "TEST-002"
    assert data["workflow_status"] == "HUMAN_REVIEW_REQUIRED"
    assert data["final_route"] == "HUMAN_REVIEW"

    assert data["summary"]["total_questions"] == 4
    assert data["summary"]["auto_fill_count"] == 3
    assert data["summary"]["human_review_count"] == 1
    assert data["summary"]["answered_count"] == 3
    assert data["summary"]["missing_count"] == 1

    annual_revenue_result = next(
        result for result in data["question_results"] if result["question_id"] == "Q3"
    )

    assert annual_revenue_result["field_name"] == "annual_revenue"
    assert annual_revenue_result["extracted_value"] is None
    assert annual_revenue_result["extraction_status"] == "MISSING"
    assert annual_revenue_result["final_route"] == "HUMAN_REVIEW"


def test_create_assessment_with_invalid_country():
    payload = {
        "case_id": "TEST-003",
        "document_text": (
            "Country of Incorporation: Mars\n"
            "Business Activity: Information Technology Services\n"
            "Annual Revenue: 10000000\n"
            "Existing Bank Relationship: Yes"
        ),
    }

    response = client.post(
        "/assessments",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["final_route"] == "HUMAN_REVIEW"
    assert data["summary"]["human_review_count"] == 1

    country_result = next(
        result for result in data["question_results"] if result["question_id"] == "Q1"
    )

    assert country_result["field_name"] == "country_of_incorporation"
    assert country_result["verification_status"] == "FAILED"
    assert country_result["final_route"] == "HUMAN_REVIEW"


def test_create_assessment_with_empty_document():
    payload = {
        "case_id": "TEST-004",
        "document_text": " ",
    }

    response = client.post(
        "/assessments",
        json=payload,
    )

    assert response.status_code == 422


def test_create_assessment_without_case_id():
    payload = {
        "document_text": (
            "Country of Incorporation: India\n"
            "Business Activity: Information Technology Services\n"
            "Annual Revenue: 10000000\n"
            "Existing Bank Relationship: Yes"
        ),
    }

    response = client.post(
        "/assessments",
        json=payload,
    )

    assert response.status_code == 422
