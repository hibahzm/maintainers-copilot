from typing import Literal

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """Base class for public API contracts."""

    model_config = ConfigDict(extra="forbid")


class FeatureStubResponse(APIModel):
    """Temporary scaffold response until a feature gets its real contract."""

    status: Literal["todo"] = "todo"
    feature: str
