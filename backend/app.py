import os
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.models import Server
from fastapi.staticfiles import StaticFiles
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette_context.middleware import RawContextMiddleware

from middleware.authentication import MuseumAuthBackend, authentication_on_error
from middleware.authorization import CasbinMiddleware
from utils import flags
from utils.utils import enforcer, get_postgres_sessionmaker

MF = flags.MuseumFlags.get()

os.makedirs("static/images", exist_ok=True)


servers = (
    Server(
        url=(
            "/"
            if MF.debug
            else (
                "https://127.0.0.1"
                if "museum-production" in MF.namespace
                else "https://museum.ottozhang.com"
            )
        ),
        description="Museum API",
    ),
)

app = FastAPI(
    title="MUSEUM",
    version=(Path(__file__).parent / "VERSION.txt").read_text(),
    description="""
    Wedding Planner API

    This API documentation is fully compatible with OpenAPI specification.

    For more information, please visit https://ottozhang.com
    """,
    openapi_tags=[
        {
            "name": "Root",
            "description": "Top-level operations",
            "externalDocs": {
                "description": "External Docs",
                "url": "https://museum.ottozhang.com",
            },
        },
        {
            "name": "Analyze",
            "description": "Artwork analysis operations",
        },
        {
            "name": "TTS",
            "description": "Text-to-speech operations",
        },
        {
            "name": "Auth",
            "description": "Authentication (e.g. Apple Sign-In)",
        },
    ],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Delayed import to avoid circularity
import routes  # noqa
from src.routes.analyze import _handle_analyze_websocket


@app.websocket("/analyze")
async def analyze_websocket(ws: WebSocket) -> None:
    """WebSocket 流式分析，路径 /analyze。"""
    await _handle_analyze_websocket(ws)


def origin(server: Server) -> str:
    parsed_uri = urlparse(server.url)
    return "{uri.scheme}://{uri.netloc}".format(uri=parsed_uri)


_global_app = None


def get_app(*_, url=None, pool_size=5, max_overflow=10, **__):
    global _global_app
    if _global_app:
        return _global_app
    _global_app = app
    _global_app.postgres_sessionmaker = get_postgres_sessionmaker(
        url=url, pool_size=pool_size, max_overflow=max_overflow
    )
    _global_app.add_middleware(CasbinMiddleware, enforcer=enforcer)
    _global_app.add_middleware(
        AuthenticationMiddleware,
        backend=MuseumAuthBackend(),
        on_error=authentication_on_error,
    )
    _global_app.add_middleware(RawContextMiddleware)
    _global_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_origin_regex=MF.allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return _global_app
