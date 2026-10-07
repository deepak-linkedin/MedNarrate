from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user, csrf_protected
from app.core.database import get_db
from app.models.db_models import User, UserProfileRecord
from app.schemas.auth import AuthResponse, LoginRequest, ProfileUpdateRequest, RegisterRequest, UserResponse
from app.services.auth_service import clear_auth_cookies, hash_password, set_auth_cookies, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

def serialize_user(user: User) -> UserResponse:
    profile = user.profile
    if profile is None:
        raise HTTPException(status_code=500, detail="User profile is missing")
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
        profile={
            "full_name": profile.full_name,
            "age": profile.age,
            "education": profile.education,
            "medical_knowledge": profile.medical_knowledge,
            "preferred_language": profile.preferred_language,
        },
    )

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    profile = UserProfileRecord(
        user_id=user.id,
        full_name=payload.full_name.strip(),
        age=payload.age,
        education=payload.education,
        medical_knowledge=payload.medical_knowledge,
        preferred_language=payload.preferred_language,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    csrf = set_auth_cookies(response, user.id)
    return AuthResponse(user=serialize_user(user), csrf_token=csrf)

@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    csrf = set_auth_cookies(response, user.id)
    return AuthResponse(user=serialize_user(user), csrf_token=csrf)

@router.post("/logout")
def logout(response: Response, _: User = Depends(csrf_protected)):
    clear_auth_cookies(response)
    return {"message": "Logged out"}

@router.get("/me", response_model=AuthResponse)
def me(request: Request, user: User = Depends(current_user)):
    from app.core.config import get_settings
    csrf = request.cookies.get(get_settings().csrf_cookie_name, "")
    return AuthResponse(user=serialize_user(user), csrf_token=csrf)

@router.put("/profile", response_model=UserResponse)
def update_profile(payload: ProfileUpdateRequest, db: Session = Depends(get_db), user: User = Depends(csrf_protected)):
    profile = user.profile
    if profile is None:
        profile = UserProfileRecord(user_id=user.id)
        db.add(profile)
    profile.full_name = payload.full_name.strip()
    profile.age = payload.age
    profile.education = payload.education
    profile.medical_knowledge = payload.medical_knowledge
    profile.preferred_language = payload.preferred_language
    db.commit()
    db.refresh(user)
    return serialize_user(user)
