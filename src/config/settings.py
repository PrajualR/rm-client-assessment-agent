from dataclasses import dataclass


@dataclass(frozen=True)
class AssessmentSettings:
    auto_fill_threshold: float = 0.85
    escalation_threshold: float = 0.60

    allowed_countries: tuple[str, ...] = (
        "India",
        "United States",
        "United Kingdom",
    )

    allowed_bank_relationship_values: tuple[str, ...] = (
        "Yes",
        "No",
    )


settings = AssessmentSettings()
