from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, chat, classifier, memory, rag, widget


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Milestone 2: replace this placeholder with a real Vault health check.
    yield


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
