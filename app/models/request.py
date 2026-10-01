"""Request schemas and validation for the chatbot endpoint."""

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    """Payload for POST /ask."""

    question: str = Field(
        ...,
        description="The natural language question to ask the chatbot.",
        examples=["Who is Batman and what are his powers?", "Tell me about Thor in Norse mythology.", "Compare Superman to Hercules."],
        min_length=2,
        max_length=1000,
    )

    @field_validator("question")
    @classmethod
    def validate_and_strip_question(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty or only whitespace.")
        return cleaned
