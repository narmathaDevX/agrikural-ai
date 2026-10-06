from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = "farmer"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[str] = "farmer"  # admin, farmer, viewer
    preferred_language: Optional[str] = "ta"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    preferred_language: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

Token.model_rebuild()
