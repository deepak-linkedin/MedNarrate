from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.core.database import get_db
from app.models.db_models import ReportSession, User
from app.schemas.api import AnalyzeResponse, ReportHistoryResponse, ReportListItem, ReportSummary
from app.schemas.extraction import MedicalFinding
from app.schemas.interpretation import ClinicalInterpretation
from app.schemas.narrative import NarrativeSpecification
from app.schemas.narrative_output import NarrativeOutput
from app.schemas.profile import UserProfile
from app.schemas.rag import EvidenceChunk
from app.schemas.safety import SafetyValidation

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("", response_model=ReportHistoryResponse)
def list_reports(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(ReportSession).where(ReportSession.user_id == user.id).order_by(ReportSession.created_at.desc())).all()
    items = []
    for row in rows:
        abnormal = sum(1 for f in row.findings if f.status in {"low", "high", "abnormal"})
        items.append(ReportListItem(id=row.id, original_filename=row.original_filename, status=row.status, created_at=row.created_at, abnormal_findings=abnormal))
    return ReportHistoryResponse(reports=items)

@router.get("/{report_id}", response_model=AnalyzeResponse)
def get_report(report_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.scalar(select(ReportSession).where(ReportSession.id == report_id, ReportSession.user_id == user.id))
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    findings = [MedicalFinding(test_name=f.test_name, value=f.value, unit=f.unit, reference_range=f.reference_range, status=f.status) for f in row.findings]
    abnormal = [f for f in findings if f.status in {"low", "high", "abnormal"}]
    normal = [f for f in findings if f.status == "normal"]
    unknown = [f for f in findings if f.status == "unknown"]
    interpretation = ClinicalInterpretation.model_validate(row.interpretation_json or {})
    profile = UserProfile(full_name=user.profile.full_name if user.profile else "User", age=row.age, education=row.education, medical_knowledge=row.medical_knowledge, preferred_language=row.preferred_language)
    questions = []
    if abnormal:
        questions.append(f"What could explain the out-of-range results involving {', '.join([f.test_name for f in abnormal[:3]])} in my situation?")
        questions.append("Should these values be compared with my previous reports or repeated later?")
    if interpretation.relationships:
        questions.append("Are the related findings in this report clinically meaningful when considered together?")
    questions.append("Do my symptoms, medical history, or other tests change how these results should be interpreted?")
    associations = []
    for item in interpretation.finding_interpretations:
        for association in item.possible_associations:
            if association not in associations:
                associations.append(association)
    return AnalyzeResponse(
        session_id=row.id,
        profile=profile,
        summary=ReportSummary(total_findings=len(findings), abnormal_findings=len(abnormal), normal_findings=len(normal), unknown_findings=len(unknown)),
        narrative=NarrativeOutput.model_validate(row.narrative_json or {}),
        important_findings=abnormal or findings[:5],
        relationships=interpretation.relationships,
        possible_patterns=interpretation.possible_patterns,
        possible_associations=associations[:8],
        limitations=interpretation.limitations,
        questions_for_clinician=questions[:4],
        sources=[EvidenceChunk.model_validate(x) for x in (row.sources_json or [])],
        safety=SafetyValidation.model_validate(row.safety_json or {}),
        findings=findings,
        interpretation=interpretation,
        narrative_specification=NarrativeSpecification.model_validate(row.narrative_spec_json or {}),
    )
