from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import AdminUserDep, AuthServiceDep, CurrentUserDep
from app.api.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
    UserRoleUpdateRequest,
)
from app.infra.exceptions import NotFoundError, PermissionDenied

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    service: AuthServiceDep,
) -> AuthTokenResponse:
    try:
        return await service.register(payload)
    except PermissionDenied as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    payload: LoginRequest,
    service: AuthServiceDep,
) -> AuthTokenResponse:
    try:
        return await service.login(email=payload.email, password=payload.password)
    except PermissionDenied as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUserDep) -> UserResponse:
    return current_user


@router.patch("/admin/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    payload: UserRoleUpdateRequest,
    admin_user: AdminUserDep,
    service: AuthServiceDep,
) -> UserResponse:
    try:
        return await service.update_role(
            actor_user_id=admin_user.id,
            user_id=user_id,
            role=payload.role,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
