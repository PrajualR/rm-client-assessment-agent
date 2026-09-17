from src.models.assessment_models import QuestionnaireQuestion

questions = [
    QuestionnaireQuestion(
        question_id="Q1",
        question="What is the client's country of incorporation?",
        field_name="country_of_incorporation",
    ),
    QuestionnaireQuestion(
        question_id="Q2",
        question="What is the client's business activity?",
        field_name="business_activity",
    ),
    QuestionnaireQuestion(
        question_id="Q3",
        question="What is the client's annual revenue?",
        field_name="annual_revenue",
    ),
    QuestionnaireQuestion(
        question_id="Q4",
        question="Does the client have an existing bank relationship?",
        field_name="existing_bank_relationship",
    ),
]
