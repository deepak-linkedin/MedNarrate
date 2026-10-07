from pydantic import BaseModel, Field


class NarrativeOutput(BaseModel):
    title: str
    explanation: str
    key_points: list[str] = Field(default_factory=list)
    important_note: str
