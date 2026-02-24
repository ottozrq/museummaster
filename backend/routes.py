from fastapi import FastAPI

from routers.analyze import router as analyze_router
from routers.tts import router as tts_router


def register_routes(app: FastAPI) -> None:
    app.include_router(analyze_router, prefix="/analyze", tags=["analyze"])
    app.include_router(tts_router, prefix="/tts", tags=["tts"])
