from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, settings
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.classifier_service import ClassifierService
from app.services.chat_tools.model_server_tools import MaintainerToolsService
from app.services.chat_tools.runner import ChatToolRunner
from app.services.conversation_state_service import ConversationStateService
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService
from app.services.widget_service import WidgetService


def get_settings() -> Settings:
    """Expose application settings through FastAPI dependency injection."""
    return settings


def get_auth_service() -> AuthService:
    return AuthService()


def get_chat_service() -> ChatService:
    return ChatService(
        rag_service=get_rag_service(),
        tool_runner=get_chat_tool_runner(),
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
    return WidgetService()


SettingsDep = Annotated[Settings, Depends(get_settings)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
ClassifierServiceDep = Annotated[ClassifierService, Depends(get_classifier_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
RagServiceDep = Annotated[RagService, Depends(get_rag_service)]
WidgetServiceDep = Annotated[WidgetService, Depends(get_widget_service)]
