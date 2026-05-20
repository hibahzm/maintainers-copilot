"""Authentication, password hashing, and signed access tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import SecretStr

from app.api.schemas.auth import AuthTokenResponse, RegisterRequest, UserResponse
from app.infra.exceptions import PermissionDenied
from app.repositories.user_repo import DuplicateUserError, UserRecord, UserRepository

_PASSWORD_ALGORITHM = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 210_000


@dataclass(frozen=True)
class TokenClaims:
    sub: UUID
    email: str
    role: str
    exp: int


class AuthService:
    """Authenticate users and mint access tokens."""

    def __init__(
        self,
        *,
        jwt_signing_key: SecretStr,
        repository: UserRepository,
        access_token_ttl_minutes: int = 60,
    ) -> None:
        self.jwt_signing_key = jwt_signing_key
        self.repository = repository
        self.access_token_ttl_minutes = access_token_ttl_minutes

    async def register(self, payload: RegisterRequest) -> AuthTokenResponse:
        email = self._normalize_email(payload.email)
        hashed_password = hash_password(payload.password)
        try:
            user = await self.repository.create_user(
                email=email,
                hashed_password=hashed_password,
                role="user",
            )
        except DuplicateUserError as exc:
            raise PermissionDenied("A user with this email already exists.") from exc
        return self._token_response(user)

    async def login(self, *, email: str, password: str) -> AuthTokenResponse:
        user = await self.repository.get_user_by_email(self._normalize_email(email))
        if user is None or not user.is_active:
            raise PermissionDenied("Invalid email or password.")
        if not verify_password(password, user.hashed_password):
            raise PermissionDenied("Invalid email or password.")
        return self._token_response(user)

    async def current_user(self, access_token: str) -> UserResponse:
        claims = decode_access_token(access_token, self.jwt_signing_key)
        user = await self.repository.get_user_by_id(claims.sub)
        if user is None or not user.is_active:
            raise PermissionDenied("User is inactive or no longer exists.")
        return UserResponse(id=user.id, email=user.email, role=user.role, is_active=user.is_active)

    def _token_response(self, user: UserRecord) -> AuthTokenResponse:
        expires_at = datetime.now(UTC) + timedelta(minutes=self.access_token_ttl_minutes)
        token = encode_access_token(
            claims={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "exp": int(expires_at.timestamp()),
            },
            signing_key=self.jwt_signing_key,
        )
        return AuthTokenResponse(
            access_token=token,
            expires_at=expires_at,
            user=UserResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
            ),
        )

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PASSWORD_ITERATIONS,
    )
    return "$".join(
        [
            _PASSWORD_ALGORITHM,
            str(_PASSWORD_ITERATIONS),
            _b64encode(salt),
            _b64encode(digest),
        ]
    )


def verify_password(password: str, encoded_password: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = encoded_password.split("$", maxsplit=3)
        if algorithm != _PASSWORD_ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64decode(salt),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(_b64encode(digest), expected_digest)


def encode_access_token(*, claims: dict, signing_key: SecretStr) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_part = _json_b64(header)
    payload_part = _json_b64(claims)
    signing_input = f"{header_part}.{payload_part}"
    signature = hmac.new(
        signing_key.get_secret_value().encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64encode(signature)}"


def decode_access_token(token: str, signing_key: SecretStr) -> TokenClaims:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}"
        expected_signature = hmac.new(
            signing_key.get_secret_value().encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_b64encode(expected_signature), signature_part):
            raise PermissionDenied("Invalid access token.")
        header = json.loads(_b64decode(header_part))
        payload = json.loads(_b64decode(payload_part))
    except (ValueError, json.JSONDecodeError) as exc:
        raise PermissionDenied("Invalid access token.") from exc

    if header.get("alg") != "HS256":
        raise PermissionDenied("Unsupported access token algorithm.")
    exp = int(payload.get("exp", 0))
    if exp < int(datetime.now(UTC).timestamp()):
        raise PermissionDenied("Access token has expired.")
    return TokenClaims(
        sub=UUID(str(payload["sub"])),
        email=str(payload["email"]),
        role=str(payload["role"]),
        exp=exp,
    )


def _json_b64(value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _b64encode(raw)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))
