"""Short-term conversation state stored in Redis with a bounded TTL."""

import json

from redis.exceptions import RedisError

from app.domain.chat import Message
from app.infra.exceptions import ToolFailure
from app.infra.redis_client import redis_client


class ConversationStateService:
    """Persist recent chat turns in Redis.

    This is short-term memory only. It is intentionally TTL-bound and separate
    from explicit long-term memory writes.
    """

    def __init__(
        self,
        *,
        redis_url: str,
        ttl_seconds: int,
        max_messages: int = 30,
        namespace: str = "chat:conversation",
    ) -> None:
        self.redis = redis_client(redis_url)
        self.ttl_seconds = ttl_seconds
        self.max_messages = max_messages
        self.namespace = namespace

    async def load_messages(self, conversation_id: str) -> list[Message]:
        try:
            raw = await self.redis.get(self._key(conversation_id))
        except RedisError as exc:
            raise ToolFailure("Short-term conversation memory is unavailable.") from exc
        if not raw:
            return []

        try:
            data = json.loads(raw)
            messages = data.get("messages", [])
            return [Message.model_validate(message) for message in messages]
        except (TypeError, ValueError) as exc:
            raise ToolFailure("Short-term conversation memory payload is invalid.") from exc

    async def save_messages(self, conversation_id: str, messages: list[Message]) -> None:
        trimmed = messages[-self.max_messages :]
        payload = {
            "conversation_id": conversation_id,
            "messages": [message.model_dump(mode="json") for message in trimmed],
            "ttl_seconds": self.ttl_seconds,
        }
        try:
            await self.redis.set(
                self._key(conversation_id),
                json.dumps(payload),
                ex=self.ttl_seconds,
            )
        except RedisError as exc:
            raise ToolFailure("Short-term conversation memory could not be saved.") from exc

    async def delete_conversation(self, conversation_id: str) -> None:
        try:
            await self.redis.delete(self._key(conversation_id))
        except RedisError as exc:
            raise ToolFailure("Short-term conversation memory could not be deleted.") from exc

    def _key(self, conversation_id: str) -> str:
        return f"{self.namespace}:{conversation_id}"
