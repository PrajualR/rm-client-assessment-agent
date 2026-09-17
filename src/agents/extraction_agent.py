from datetime import datetime, timezone

from src.models.assessment_models import ExtractionResult
from src.utils.question_helpers import get_question_value


def extract_value_from_document(document_text: str, field_name: str):
    """
    Extract a field value from the plain-text mock document.

    Expected document format:

    Country of Incorporation: India
    Business Activity: Information Technology Services
    Annual Revenue: 10000000
    Existing Bank Relationship: Yes
    """

    field_labels = {
        "country_of_incorporation": "Country of Incorporation",
        "business_activity": "Business Activity",
        "annual_revenue": "Annual Revenue",
        "existing_bank_relationship": "Existing Bank Relationship",
    }

    label = field_labels.get(field_name)

    if not label:
        return None

    for line in document_text.splitlines():
        line = line.strip()

        if line.lower().startswith(f"{label.lower()}:"):
            value = line.split(":", 1)[1].strip()

            if value:
                return value

    return None


def extraction_agent(state):
    """
    Extract answers for every questionnaire question.
    """

    try:
        document_text = state["document_text"]
        questions = state["questions"]

        if not isinstance(document_text, str):
            raise TypeError("Document content must be a string.")

        extracted_data = {}
        question_results = {}

        for question in questions:
            question_id = get_question_value(question, "question_id")
            question_text = get_question_value(question, "question")
            field_name = get_question_value(question, "field_name")

            if not question_id or not field_name:
                raise ValueError(
                    "Each questionnaire question must contain "
                    "'question_id' and 'field_name'."
                )

            extracted_value = extract_value_from_document(
                document_text=document_text,
                field_name=field_name,
            )

            extraction_status = "FOUND" if extracted_value is not None else "MISSING"

            extraction_result = ExtractionResult(
                question_id=question_id,
                field_name=field_name,
                extracted_value=extracted_value,
                extraction_status=extraction_status,
            )

            extracted_data[field_name] = extracted_value

            question_results[question_id] = {
                "question_id": question_id,
                "question": question_text,
                "field_name": field_name,
                "extracted_value": extracted_value,
                "extraction_status": extraction_status,
            }

        audit_log = list(state.get("audit_log", []))

        audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc),
                "agent": "ExtractionAgent",
                "action": "Extracted questionnaire answers",
                "input": {
                    "question_count": len(questions),
                },
                "output": {
                    "extraction_status": "success",
                    "extracted_field_count": len(extracted_data),
                },
            }
        )

        return {
            **state,
            "extraction_status": "success",
            "extracted_data": extracted_data,
            "question_results": question_results,
            "audit_log": audit_log,
        }

    except Exception as exc:
        errors = list(state.get("errors", []))
        audit_log = list(state.get("audit_log", []))

        errors.append(
            {
                "timestamp": datetime.now(timezone.utc),
                "agent": "ExtractionAgent",
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        )

        audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc),
                "agent": "ExtractionAgent",
                "action": "Document extraction failed",
                "input": {
                    "question_count": len(state.get("questions", [])),
                },
                "output": {
                    "extraction_status": "failed",
                    "error": str(exc),
                },
            }
        )

        return {
            **state,
            "extraction_status": "failed",
            "extracted_data": {},
            "question_results": {},
            "errors": errors,
            "audit_log": audit_log,
            "final_route": "HUMAN_REVIEW",
        }
