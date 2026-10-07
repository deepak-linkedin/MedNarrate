import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.db_models import User, UserProfileRecord

settings = get_settings()

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iter_text, salt_text, digest_text = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iter_text))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=settings.jwt_expire_minutes)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def set_auth_cookies(response: Response, user_id: str) -> str:
    token = create_access_token(user_id)
    csrf = create_csrf_token()
    common = dict(path="/", secure=settings.cookie_secure, samesite=settings.cookie_samesite, domain=settings.cookie_domain or None)
    response.set_cookie(settings.cookie_name, token, httponly=True, max_age=settings.jwt_expire_minutes * 60, **common)
    response.set_cookie(settings.csrf_cookie_name, csrf, httponly=False, max_age=settings.jwt_expire_minutes * 60, **common)
    return csrf

def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.cookie_name, path="/", domain=settings.cookie_domain or None)
    response.delete_cookie(settings.csrf_cookie_name, path="/", domain=settings.cookie_domain or None)

def get_user_from_request(request: Request, db: Session) -> User:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Missing subject")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session") from exc
    user = db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account unavailable")
    return user

def verify_csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    cookie = request.cookies.get(settings.csrf_cookie_name, "")
    header = request.headers.get("X-CSRF-Token", "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
