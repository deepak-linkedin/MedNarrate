from pydantic import BaseModel, Field


class SafetyValidation(BaseModel):
    passed: bool
    preserved_values: bool
    preserved_units: bool
    unsupported_diagnosis_detected: bool = False
    treatment_language_detected: bool = False
    issues: list[str] = Field(default_factory=list)
