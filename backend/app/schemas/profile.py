from typing import Literal
from pydantic import BaseModel, Field
MedicalKnowledge = Literal["Beginner", "Intermediate", "Advanced"]

class UserProfile(BaseModel):
    full_name: str = Field(default="User", min_length=1, max_length=120)
    age: int = Field(ge=1, le=120)
    education: str = Field(min_length=1, max_length=120)
    medical_knowledge: MedicalKnowledge
    preferred_language: str = Field(default="English", min_length=1, max_length=50)
