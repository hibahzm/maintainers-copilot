from fastapi import FastAPI

from model_server.classifier.inference import router as classifier_router
from model_server.ner.inference import router as ner_router
from model_server.summarizer.inference import router as summarizer_router

app = FastAPI(title="Maintainers Copilot Model Server")
app.include_router(classifier_router)
app.include_router(ner_router)
app.include_router(summarizer_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
