from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.schemas.profile import MedicalKnowledge

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=1, le=120)
    education: str = Field(min_length=1, max_length=120)
    medical_knowledge: MedicalKnowledge
    preferred_language: str = Field(default="English", min_length=1, max_length=50)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=1, le=120)
    education: str = Field(min_length=1, max_length=120)
    medical_knowledge: MedicalKnowledge
    preferred_language: str = Field(default="English", min_length=1, max_length=50)

class ProfileResponse(BaseModel):
    full_name: str
    age: int
    education: str
    medical_knowledge: str
    preferred_language: str

class UserResponse(BaseModel):
    id: str
    email: str
    is_active: bool
    created_at: datetime
    profile: ProfileResponse

class AuthResponse(BaseModel):
    user: UserResponse
    csrf_token: str
