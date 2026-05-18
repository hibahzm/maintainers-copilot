from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, chat, classifier, memory, rag, widget
from app.core.config import settings
from app.infra.vault import VaultClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    vault = VaultClient(settings)
    try:
        await vault.assert_reachable()
        app.state.runtime_secrets = await vault.load_runtime_secrets()
        yield
    finally:
        await vault.aclose()


app = FastAPI(title="Maintainers Copilot API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(classifier.router)
app.include_router(rag.router)
app.include_router(memory.router)
app.include_router(widget.router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
