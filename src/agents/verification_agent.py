import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from src.config.settings import settings
from src.models.assessment_models import VerificationResult


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_annual_revenue(value) -> float | None:
    """
    Convert common annual revenue formats into a numeric value.

    Supported examples:

    10000000
    "10000000"
    "INR 48.5 Crores"
    "₹48.5 crore"
    "48.5 Cr"
    "INR 2.5 Lakhs"
    "2.5 lakh"
    "USD 10 million"

    Examples:

    INR 48.5 Crores -> 485000000.0
    INR 2.5 Lakhs   -> 250000.0
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


def verify_field(
    field_name: str,
    value,
) -> VerificationResult:
    """
    Verify one extracted field using deterministic business rules.

    The original extracted value is retained in the result.
    Annual revenue is normalized internally before validation.
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
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="PASSED",
                confidence=0.95,
                reason=(
                    "Country is present in the configured " "allowed-country list."
                ),
            )

        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="FAILED",
            confidence=0.30,
            reason=(
                "Country is not present in the configured " "allowed-country list."
            ),
        )

    if field_name == "business_activity":
        if len(normalized_value) >= 3:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="PASSED",
                confidence=0.95,
                reason=("Business activity contains a valid " "descriptive value."),
            )

        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="FAILED",
            confidence=0.30,
            reason="Business activity value is too short.",
        )

    if field_name == "annual_revenue":
        normalized_revenue = normalize_annual_revenue(value)

        if normalized_revenue is None:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="FAILED",
                confidence=0.30,
                reason=(
                    "Annual revenue must be a valid, "
                    "non-negative numeric or supported "
                    "financial value."
                ),
            )

        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="PASSED",
            confidence=0.95,
            reason=("Annual revenue is a valid, non-negative " "financial value."),
        )

    if field_name == "existing_bank_relationship":
        if normalized_value in settings.allowed_bank_relationship_values:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="PASSED",
                confidence=0.95,
                reason=("Bank relationship value is valid."),
            )

        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="FAILED",
            confidence=0.30,
            reason=("Bank relationship must be Yes or No."),
        )

    return VerificationResult(
        field_name=field_name,
        value=value,
        verification_status="REVIEW_REQUIRED",
        confidence=0.50,
        reason=("No verification rule is configured " "for this field."),
    )


def verification_agent(state):
    """
    Verify all extracted questionnaire answers.
    """

    try:
        verification_results = {}
        question_results = dict(state.get("question_results", {}))

        for question in state["questions"]:
            question_id = question.question_id
            field_name = question.field_name

            extracted_result = question_results.get(
                question_id,
                {},
            )

            extracted_value = extracted_result.get("extracted_value")

            verification_result = verify_field(
                field_name=field_name,
                value=extracted_value,
            )

            verification_results[field_name] = verification_result.model_dump()

            question_results[question_id] = {
                **extracted_result,
                "verification_status": (verification_result.verification_status),
                "verification_confidence": (verification_result.confidence),
                "verification_reason": (verification_result.reason),
            }

        audit_log = list(state.get("audit_log", []))

        audit_log.append(
            {
                "timestamp": utc_timestamp(),
                "agent": "VerificationAgent",
                "action": "Verified questionnaire answers",
                "input": {
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
            "audit_log": audit_log,
        }

    except Exception as exc:
        errors = list(state.get("errors", []))

        audit_log = list(state.get("audit_log", []))

        error_details = {
            "timestamp": utc_timestamp(),
            "agent": "VerificationAgent",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }

        errors.append(error_details)

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
            "verification_results": {},
            "question_results": question_results,
            "errors": errors,
            "audit_log": audit_log,
            "final_route": "HUMAN_REVIEW",
        }
