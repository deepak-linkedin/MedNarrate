from sqlalchemy.orm import Session
from app.models.db_models import ReportSession, FindingRecord
from app.schemas.profile import UserProfile


def persist_result(db: Session, user_id: str, filename: str, profile: UserProfile, findings, interpretation, spec, narrative, safety, sources) -> str:
    session = ReportSession(
        user_id=user_id,
        original_filename=filename,
        age=profile.age,
        education=profile.education,
        medical_knowledge=profile.medical_knowledge,
        preferred_language=profile.preferred_language,
        status="completed",
        interpretation_json=interpretation.model_dump(),
        narrative_spec_json=spec.model_dump(),
        narrative_json=narrative.model_dump(),
        safety_json=safety.model_dump(),
        sources_json=[s.model_dump() for s in sources],
    )
    db.add(session)
    db.flush()
    for finding in findings:
        db.add(FindingRecord(session_id=session.id, **finding.model_dump()))
    db.commit()
    db.refresh(session)
    return session.id
