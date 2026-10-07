from typing import Literal
from pydantic import BaseModel, Field


class MedicalFinding(BaseModel):
    finding_type: Literal[
        "laboratory",
        "imaging",
        "cardiology",
        "pathology",
        "diagnosis",
        "symptom",
        "other",
    ] = "other"

    test_name: str

    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None

    description: str | None = None

    status: Literal[
        "low",
        "normal",
        "high",
        "abnormal",
        "diagnostic",
        "unknown",
    ] = "unknown"


class MedicalFindingsResponse(BaseModel):
    findings: list[MedicalFinding] = Field(default_factory=list)