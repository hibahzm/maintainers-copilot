from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, settings
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.classifier_service import ClassifierService
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService
from app.services.widget_service import WidgetService


def get_settings() -> Settings:
    """Expose application settings through FastAPI dependency injection."""
    return settings


def get_auth_service() -> AuthService:
    return AuthService()


def get_chat_service() -> ChatService:
    return ChatService(rag_service=get_rag_service())


def get_classifier_service() -> ClassifierService:
    return ClassifierService(model_server_url=settings.model_server_url)


def get_memory_service() -> MemoryService:
    return MemoryService()


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
