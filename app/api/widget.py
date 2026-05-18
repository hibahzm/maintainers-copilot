from fastapi import APIRouter

router = APIRouter(prefix="/widget", tags=["widget"])


@router.get("/config/{widget_id}")
async def get_widget_config(widget_id: str) -> dict[str, str]:
    return {"status": "todo", "widget_id": widget_id}


@router.get("/widget.js")
async def widget_loader() -> dict[str, str]:
    return {"status": "todo", "feature": "widget loader"}
