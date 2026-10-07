from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.api.deps import csrf_protected
from app.core.config import get_settings
from app.core.database import get_db
from app.models.db_models import User
from app.schemas.api import AnalyzeResponse
from app.schemas.profile import UserProfile
from app.services.mednarrate_pipeline import process_report

router = APIRouter(tags=["analysis"])
settings = get_settings()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_report(
    report: UploadFile = File(...),
    debug: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(csrf_protected),
):
    try:
        if user.profile is None:
            raise ValueError("Complete your profile before analyzing a report.")
        profile = UserProfile(
            full_name=user.profile.full_name,
            age=user.profile.age,
            education=user.profile.education,
            medical_knowledge=user.profile.medical_knowledge,
            preferred_language=user.profile.preferred_language,
        )
        content = await report.read()
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise ValueError(f"File is too large. Maximum size is {settings.max_upload_mb} MB.")
        return process_report(report.filename or "report", content, profile, user.id, db, debug)
    except HTTPException:
        raise
    # except Exception as exc:
    #     raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        import traceback

        print("\n========== ANALYSIS ERROR ==========")
        traceback.print_exc()
        print("====================================\n")

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc
