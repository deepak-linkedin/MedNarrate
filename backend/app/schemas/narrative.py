from typing import Literal
from pydantic import BaseModel


class NarrativeSpecification(BaseModel):
    vocabulary_level: Literal["very_simple", "simple", "moderate", "technical"]
    sentence_complexity: Literal["low", "moderate", "high"]
    technical_terms: Literal["minimal", "moderate", "high"]
    analogy_usage: Literal["low", "moderate", "high"]
    detail_level: Literal["low", "moderate", "high"]
    causal_explanation: Literal["simple", "logical", "clinical"]
    tone: Literal[
        "friendly_and_reassuring",
        "clear_and_reassuring",
        "informative_and_reassuring",
        "clinical_and_precise",
    ]
    structure: list[str]
    guidance: list[str]
