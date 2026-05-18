from typing import Literal

from pydantic import Field

from app.api.schemas.common import APIModel


class RegisterRequest(APIModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(APIModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class AuthTokenResponse(APIModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
