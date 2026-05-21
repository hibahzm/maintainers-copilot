from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr

from app.api.schemas.auth import UserResponse
from app.core.config import Settings, settings
from app.infra.exceptions import PermissionDenied
from app.repositories.user_repo import UserRepository
from app.repositories.widget_repo import WidgetRepository
from app.services.auth_service import AuthService
from app.services.chat_agent.openai_agent import OpenAIChatAgentService
from app.services.chat_service import ChatService
from app.services.classifier_service import ClassifierService
from app.services.chat_tools.model_server_tools import MaintainerToolsService
from app.services.chat_tools.runner import ChatToolRunner
from app.services.conversation_state_service import ConversationStateService
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService
from app.services.widget_service import WidgetService

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    """Expose application settings through FastAPI dependency injection."""
    return settings


def _runtime_secret(
    request: Request,
    name: str,
    *,
    fallback: SecretStr | None = None,
) -> SecretStr | None:
    runtime_secrets = getattr(request.app.state, "runtime_secrets", None)
    value = getattr(runtime_secrets, name, None) if runtime_secrets else None
    if isinstance(value, SecretStr) and value.get_secret_value():
        return value
    if fallback and fallback.get_secret_value():
        return fallback
    return None


def get_auth_service(request: Request) -> AuthService:
    return AuthService(
        jwt_signing_key=_runtime_secret(
            request,
            "jwt_signing_key",
            fallback=settings.jwt_signing_key,
        )
        or SecretStr("dev-only-jwt-signing-key"),
        repository=get_user_repository(),
        access_token_ttl_minutes=settings.access_token_ttl_minutes,
    )


def get_user_repository() -> UserRepository:
    return UserRepository(database_url=settings.database_url)


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse | None:
    if credentials is None:
        return None
    try:
        return await service.current_user(credentials.credentials)
    except PermissionDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


async def get_current_user(
    current_user: Annotated[UserResponse | None, Depends(get_optional_current_user)],
) -> UserResponse:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    return current_user


async def require_admin(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required.",
        )
    return current_user


def get_chat_service(request: Request) -> ChatService:
    return ChatService(
        rag_service=get_rag_service(),
        tool_runner=get_chat_tool_runner(),
        agent_service=get_openai_chat_agent_service(request),
        conversation_state_service=get_conversation_state_service(),
    )


def get_classifier_service() -> ClassifierService:
    return ClassifierService(model_server_url=settings.model_server_url)


def get_conversation_state_service() -> ConversationStateService:
    return ConversationStateService(
        redis_url=settings.redis_url,
        ttl_seconds=settings.conversation_ttl_seconds,
    )


def get_chat_tool_runner() -> ChatToolRunner:
    return ChatToolRunner(
        tools_service=get_maintainer_tools_service(),
        memory_service=get_memory_service(),
    )


def get_openai_chat_agent_service(request: Request) -> OpenAIChatAgentService:
    return OpenAIChatAgentService(
        api_key=_runtime_secret(request, "llm_api_key", fallback=settings.openai_api_key),
        model=settings.chat_agent_model,
        rag_service=get_rag_service(),
        tool_runner=get_chat_tool_runner(),
        max_tool_rounds=settings.chat_agent_max_tool_rounds,
    )


def get_maintainer_tools_service() -> MaintainerToolsService:
    return MaintainerToolsService(model_server_url=settings.model_server_url)


def get_memory_service() -> MemoryService:
    return MemoryService(
        database_url=settings.database_url,
        model_server_url=settings.model_server_url,
    )


def get_rag_service() -> RagService:
    return RagService(
        model_server_url=settings.model_server_url,
        database_url=settings.database_url,
    )


def get_widget_service() -> WidgetService:
    return WidgetService(repository=get_widget_repository())


def get_widget_repository() -> WidgetRepository:
    return WidgetRepository(database_url=settings.database_url)


SettingsDep = Annotated[Settings, Depends(get_settings)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
OptionalCurrentUserDep = Annotated[UserResponse | None, Depends(get_optional_current_user)]
CurrentUserDep = Annotated[UserResponse, Depends(get_current_user)]
AdminUserDep = Annotated[UserResponse, Depends(require_admin)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
ClassifierServiceDep = Annotated[ClassifierService, Depends(get_classifier_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
RagServiceDep = Annotated[RagService, Depends(get_rag_service)]
WidgetServiceDep = Annotated[WidgetService, Depends(get_widget_service)]
