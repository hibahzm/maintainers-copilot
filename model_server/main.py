from contextlib import asynccontextmanager

from fastapi import FastAPI

from model_server.routers.classifier import router as classifier_router
from model_server.routers.embedder import router as embedder_router
from model_server.routers.ner import router as ner_router
from model_server.routers.rag_answer import router as rag_answer_router
from model_server.routers.summarizer import router as summarizer_router
from model_server.services.startup_checks import (
    assert_classifier_artifact_ready,
    assert_llm_secret_available,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    assert_classifier_artifact_ready()
    assert_llm_secret_available()
    yield


app = FastAPI(title="Maintainers Copilot Model Server", lifespan=lifespan)
app.include_router(classifier_router)
app.include_router(embedder_router)
app.include_router(ner_router)
app.include_router(rag_answer_router)
app.include_router(summarizer_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
