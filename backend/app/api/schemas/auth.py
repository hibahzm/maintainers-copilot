from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.api.schemas.common import APIModel

UserRole = Literal["user", "admin"]


class RegisterRequest(APIModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(APIModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(APIModel):
    id: UUID
    email: str
    role: UserRole
    is_active: bool


class AuthTokenResponse(APIModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: UserResponse
