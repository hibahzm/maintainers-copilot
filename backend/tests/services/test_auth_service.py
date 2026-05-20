from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.api.schemas.auth import RegisterRequest
from app.infra.exceptions import PermissionDenied
from app.repositories.user_repo import DuplicateUserError, UserRecord
from app.services.auth_service import (
    AuthService,
    decode_access_token,
    encode_access_token,
    hash_password,
    verify_password,
)


class FakeUserRepository:
    def __init__(self):
        self.users_by_email = {}
        self.users_by_id = {}

    async def create_user(self, *, email, hashed_password, role="user"):
        if email in self.users_by_email:
            raise DuplicateUserError("duplicate")
        record = UserRecord(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        self.users_by_email[email] = record
        self.users_by_id[record.id] = record
        return record

    async def get_user_by_email(self, email):
        return self.users_by_email.get(email)

    async def get_user_by_id(self, user_id):
        return self.users_by_id.get(user_id)


def test_password_hash_verification_roundtrip():
    encoded = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


@pytest.mark.asyncio
async def test_register_normalizes_email_and_returns_token():
    service = AuthService(
        jwt_signing_key=SecretStr("test-secret"),
        repository=FakeUserRepository(),
    )

    token = await service.register(
        RegisterRequest(email="Hiba@Example.COM", password="strong-password")
    )

    assert token.user.email == "hiba@example.com"
    assert token.user.role == "user"
    assert token.access_token.count(".") == 2


@pytest.mark.asyncio
async def test_login_rejects_bad_password():
    repository = FakeUserRepository()
    service = AuthService(jwt_signing_key=SecretStr("test-secret"), repository=repository)
    await service.register(RegisterRequest(email="hiba@example.com", password="strong-password"))

    with pytest.raises(PermissionDenied):
        await service.login(email="hiba@example.com", password="wrong-password")


def test_decode_access_token_rejects_expired_token():
    secret = SecretStr("test-secret")
    token = encode_access_token(
        claims={
            "sub": str(uuid4()),
            "email": "hiba@example.com",
            "role": "user",
            "exp": int((datetime.now(UTC) - timedelta(minutes=1)).timestamp()),
        },
        signing_key=secret,
    )

    with pytest.raises(PermissionDenied):
        decode_access_token(token, secret)
