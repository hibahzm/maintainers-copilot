from fastapi import APIRouter

from app.api.dependencies import AuthServiceDep
from app.api.schemas.auth import LoginRequest, RegisterRequest
from app.api.schemas.common import FeatureStubResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=FeatureStubResponse)
async def register(
    payload: RegisterRequest,
    service: AuthServiceDep,
) -> FeatureStubResponse:
    _ = payload, service
    return FeatureStubResponse(feature="register")


@router.post("/login", response_model=FeatureStubResponse)
async def login(
    payload: LoginRequest,
    service: AuthServiceDep,
) -> FeatureStubResponse:
    _ = payload, service
    return FeatureStubResponse(feature="login")
