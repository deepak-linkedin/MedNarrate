from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.extraction import MedicalFinding
from app.schemas.interpretation import ClinicalInterpretation
from app.schemas.narrative import NarrativeSpecification
from app.schemas.narrative_output import NarrativeOutput
from app.schemas.profile import UserProfile
from app.schemas.rag import EvidenceChunk
from app.schemas.safety import SafetyValidation
from pydantic import BaseModel


class MedicalSource(BaseModel):
    title: str
    organization: str
    topic: str | None = None
    url: str | None = None
    origin: str | None = None

class ReportSummary(BaseModel):
    total_findings: int
    abnormal_findings: int
    normal_findings: int
    unknown_findings: int

# class AnalyzeResponse(BaseModel):
#     session_id: str
#     profile: UserProfile
#     summary: ReportSummary
#     narrative: NarrativeOutput
#     important_findings: list[MedicalFinding]
#     relationships: list[str] = Field(default_factory=list)
#     possible_patterns: list[str] = Field(default_factory=list)
#     possible_associations: list[str] = Field(default_factory=list)
#     limitations: list[str] = Field(default_factory=list)
#     questions_for_clinician: list[str] = Field(default_factory=list)
#     sources: list[EvidenceChunk] = Field(default_factory=list)
#     safety: SafetyValidation
#     findings: list[MedicalFinding] | None = None
#     interpretation: ClinicalInterpretation | None = None
#     narrative_specification: NarrativeSpecification | None = None

class AnalyzeResponse(BaseModel):
    session_id: str

    profile: UserProfile
    summary: ReportSummary

    narrative: NarrativeOutput

    important_findings: list[MedicalFinding]

    relationships: list[str]
    possible_patterns: list[str]
    possible_associations: list[str]

    limitations: list[str]
    questions_for_clinician: list[str]

    sources: list[MedicalSource]

    safety: SafetyValidation

    findings: list[MedicalFinding] | None = None
    interpretation: ClinicalInterpretation | None = None
    narrative_specification: NarrativeSpecification

class ReportListItem(BaseModel):
    id: str
    original_filename: str
    status: str
    created_at: datetime
    abnormal_findings: int

class ReportHistoryResponse(BaseModel):
    reports: list[ReportListItem]
