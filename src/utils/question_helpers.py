def get_question_value(question, field_name: str):
    """
    Read a questionnaire field from either:
    - a Pydantic QuestionnaireQuestion model
    - a normal dictionary
    """

    if isinstance(question, dict):
        return question.get(field_name)

    return getattr(question, field_name, None)
