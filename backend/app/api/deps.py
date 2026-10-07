from fastapi import Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import User
from app.services.auth_service import get_user_from_request, verify_csrf

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return get_user_from_request(request, db)

def csrf_protected(request: Request, user: User = Depends(current_user)) -> User:
    verify_csrf(request)
    return user
