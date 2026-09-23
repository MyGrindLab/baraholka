from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.infrastructure.mongo import get_mongo_db

router = APIRouter()


@router.get("/health")
async def health_check(db=Depends(get_mongo_db)) -> JSONResponse:
    await db.command("ping")

    return JSONResponse(content={"database": "connected", "app_status": "running"})
