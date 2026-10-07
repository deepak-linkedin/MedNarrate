from pydantic import BaseModel, Field


class FindingInterpretation(BaseModel):
    test_name: str
    meaning: str
    significance: str
    possible_associations: list[str] = Field(default_factory=list)
    uncertainty: str | None = None


class ClinicalInterpretation(BaseModel):
    overall_summary: str
    finding_interpretations: list[FindingInterpretation] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    possible_patterns: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
