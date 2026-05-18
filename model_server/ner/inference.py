from fastapi import APIRouter

router = APIRouter(tags=["ner"])


@router.post("/ner")
async def extract_entities() -> dict[str, str]:
    return {"status": "todo", "feature": "entity extraction"}
