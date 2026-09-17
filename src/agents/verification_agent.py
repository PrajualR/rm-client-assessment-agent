import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from data.mock_verified_client import verified_client_data
from src.config.settings import settings
from src.models.assessment_models import VerificationResult


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str | None:
    """
    Normalize text values for comparison.

    Example:
        " Information Technology Services "
        -> "information technology services"
    """
    if value is None:
        return None

    normalized = str(value).strip().lower()

    if not normalized:
        return None

    return normalized


def normalize_annual_revenue(value: Any) -> float | None:
    """
    Convert supported financial formats into a numeric value.

    Examples:
        "10000000"          -> 10000000.0
        "INR 48.5 Crores"   -> 485000000.0
        "₹48.5 crore"       -> 485000000.0
        "INR 2.5 Lakhs"     -> 250000.0
        "USD 10 million"    -> 10000000.0
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float, Decimal)):
        numeric_value = float(value)

        if numeric_value < 0:
            return None

        return numeric_value

    normalized = str(value).strip().lower()

    if not normalized:
        return None

    normalized = normalized.replace(",", "")
    normalized = normalized.replace("₹", "")
    normalized = normalized.replace("$", "")
    normalized = normalized.replace("€", "")
    normalized = normalized.replace("£", "")

    normalized = re.sub(r"\binr\b", "", normalized)
    normalized = re.sub(r"\brs\.?\b", "", normalized)
    normalized = re.sub(r"\busd\b", "", normalized)
    normalized = re.sub(r"\beur\b", "", normalized)
    normalized = re.sub(r"\bgbp\b", "", normalized)

    normalized = normalized.strip()

    multiplier = 1

    if (
        "crore" in normalized
        or "crores" in normalized
        or re.search(r"\bcr\b", normalized)
    ):
        multiplier = 10_000_000

    elif (
        "lakh" in normalized
        or "lakhs" in normalized
        or re.search(r"\blac\b", normalized)
    ):
        multiplier = 100_000

    elif "million" in normalized:
        multiplier = 1_000_000

    elif "billion" in normalized:
        multiplier = 1_000_000_000

    number_match = re.search(
        r"-?\d+(?:\.\d+)?",
        normalized,
    )

    if not number_match:
        return None

    try:
        number = Decimal(number_match.group())
        result = number * multiplier

        if result < 0:
            return None

        return float(result)

    except InvalidOperation:
        return None


def values_match(field_name: str, extracted_value: Any, trusted_value: Any) -> bool:
    """
    Compare an extracted value with the trusted client value.
    """

    if field_name == "annual_revenue":
        extracted_revenue = normalize_annual_revenue(extracted_value)
        trusted_revenue = normalize_annual_revenue(trusted_value)

        if extracted_revenue is None or trusted_revenue is None:
            return False

        return extracted_revenue == trusted_revenue

    extracted_text = normalize_text(extracted_value)
    trusted_text = normalize_text(trusted_value)

    if extracted_text is None or trusted_text is None:
        return False

    return extracted_text == trusted_text


def verify_field(
    field_name: str,
    value: Any,
    trusted_value: Any = None,
) -> VerificationResult:
    """
    Verify an extracted field using:

    1. Basic deterministic validation.
    2. Independent comparison with trusted client data.
    """

    if value is None or str(value).strip() == "":
        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="REVIEW_REQUIRED",
            confidence=0.0,
            reason="Value is missing and requires human review.",
        )

    normalized_value = str(value).strip()

    if field_name == "country_of_incorporation":
        if normalized_value in settings.allowed_countries:
            basic_validation_passed = True
        else:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="FAILED",
                confidence=0.30,
                reason="Country is not in the configured allowed-country list.",
            )

    elif field_name == "business_activity":
        if len(normalized_value) >= 3:
            basic_validation_passed = True
        else:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="FAILED",
                confidence=0.30,
                reason="Business activity value is too short.",
            )

    elif field_name == "annual_revenue":
        if normalize_annual_revenue(value) is not None:
            basic_validation_passed = True
        else:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="FAILED",
                confidence=0.30,
                reason="Annual revenue is not a valid supported financial value.",
            )

    elif field_name == "existing_bank_relationship":
        if normalized_value in settings.allowed_bank_relationship_values:
            basic_validation_passed = True
        else:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="FAILED",
                confidence=0.30,
                reason="Bank relationship must be Yes or No.",
            )

    else:
        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="REVIEW_REQUIRED",
            confidence=0.50,
            reason="No verification rule is configured for this field.",
        )

    if not basic_validation_passed:
        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="REVIEW_REQUIRED",
            confidence=0.50,
            reason="Basic field validation could not be completed.",
        )

    if trusted_value is None:
        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="REVIEW_REQUIRED",
            confidence=0.50,
            reason="Trusted client value is unavailable.",
        )

    if values_match(
        field_name=field_name,
        extracted_value=value,
        trusted_value=trusted_value,
    ):
        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="PASSED",
            confidence=0.95,
            reason="Extracted value passed validation and matched trusted client data.",
        )

    return VerificationResult(
        field_name=field_name,
        value=value,
        verification_status="FAILED",
        confidence=0.30,
        reason="Extracted value did not match trusted client data.",
    )


def verification_agent(state):
    """
    Verify extracted questionnaire answers against an independent
    trusted client data source.
    """

    verification_results = {}
    question_results = dict(state.get("question_results", {}))
    errors = list(state.get("errors", []))
    audit_log = list(state.get("audit_log", []))

    try:
        case_id = state["case_id"]
        trusted_client = verified_client_data.get(case_id)

        if trusted_client is None:
            audit_log.append(
                {
                    "timestamp": utc_timestamp(),
                    "agent": "VerificationAgent",
                    "action": "Trusted client record not found",
                    "input": {
                        "case_id": case_id,
                    },
                    "output": {
                        "verification_status": "failed",
                        "reason": "No trusted client record exists for the case.",
                    },
                }
            )

            return {
                **state,
                "verification_status": "success",
                "verification_results": {},
                "question_results": question_results,
                "audit_log": audit_log,
                "final_route": "HUMAN_REVIEW",
            }

        for question in state["questions"]:
            question_id = question.question_id
            field_name = question.field_name

            extracted_result = question_results.get(question_id, {})
            extracted_value = extracted_result.get("extracted_value")
            trusted_value = trusted_client.get(field_name)

            verification_result = verify_field(
                field_name=field_name,
                value=extracted_value,
                trusted_value=trusted_value,
            )

            verification_results[field_name] = verification_result.model_dump()

            question_results[question_id] = {
                **extracted_result,
                "verification_status": verification_result.verification_status,
                "verification_confidence": verification_result.confidence,
                "verification_reason": verification_result.reason,
                "trusted_value": trusted_value,
            }

        audit_log.append(
            {
                "timestamp": utc_timestamp(),
                "agent": "VerificationAgent",
                "action": "Compared extracted answers with trusted client data",
                "input": {
                    "case_id": case_id,
                    "question_count": len(state["questions"]),
                },
                "output": {
                    "verification_status": "success",
                    "verified_field_count": len(verification_results),
                },
            }
        )

        return {
            **state,
            "verification_status": "success",
            "verification_results": verification_results,
            "question_results": question_results,
            "errors": errors,
            "audit_log": audit_log,
        }

    except Exception as exc:
        errors.append(
            {
                "timestamp": utc_timestamp(),
                "agent": "VerificationAgent",
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        )

        audit_log.append(
            {
                "timestamp": utc_timestamp(),
                "agent": "VerificationAgent",
                "action": "Verification failed",
                "input": {
                    "question_count": len(state.get("questions", [])),
                },
                "output": {
                    "verification_status": "failed",
                    "error": str(exc),
                },
            }
        )

        return {
            **state,
            "verification_status": "failed",
            "verification_results": verification_results,
            "question_results": question_results,
            "errors": errors,
            "audit_log": audit_log,
            "final_route": "HUMAN_REVIEW",
        }