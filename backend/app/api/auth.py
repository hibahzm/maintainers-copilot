from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import AuthServiceDep, CurrentUserDep
from app.api.schemas.auth import AuthTokenResponse, LoginRequest, RegisterRequest, UserResponse
from app.infra.exceptions import PermissionDenied

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
