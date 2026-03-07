import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import casbin
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.models import Server
from fastapi.staticfiles import StaticFiles
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette_context.middleware import RawContextMiddleware

from middleware.authentication import MuseumAuthBackend, authentication_on_error
from middleware.authorization import CasbinMiddleware
from routers.analyze import _handle_analyze_websocket
from routes import register_routes
from utils import flags

load_dotenv()

MF = flags.MuseumFlags.get()

# Setup logging
logging.basicConfig(level=logging.DEBUG if MF.debug else logging.INFO)


# Create Casbin enforcer
def get_enforcer():
    policy_dir = Path(__file__).parent / "policy"
    return casbin.Enforcer(
        str(policy_dir / "model.conf"), str(policy_dir / "policy.csv")
    )


enforcer = get_enforcer()

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
        description="Museum Guide API",
    ),
)

app = FastAPI(
    title="Museum Guide API",
    version="0.1.0",
    description="""
    Museum Guide API

    This API documentation is fully compatible with OpenAPI specification.

    For more information, please visit https://museum.ottozhang.com
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
            "externalDocs": {
                "description": "Analyze API Documentation",
                "url": "https://museum.ottozhang.com",
            },
        },
        {
            "name": "TTS",
            "description": "Text-to-speech operations",
            "externalDocs": {
                "description": "TTS API Documentation",
                "url": "https://museum.ottozhang.com",
            },
        },
    ],
)

# Ensure static files directory exists
os.makedirs("static/images", exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


def origin(server: Server) -> str:
    parsed_uri = urlparse(server.url)
    return "{uri.scheme}://{uri.netloc}".format(uri=parsed_uri)


def get_app(*_, url=None, pool_size=5, max_overflow=10, **__):
    global app

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_origin_regex=MF.allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add Casbin middleware
    app.add_middleware(CasbinMiddleware, enforcer=enforcer)

    # Add authentication middleware
    app.add_middleware(
        AuthenticationMiddleware,
        backend=MuseumAuthBackend(),
        on_error=authentication_on_error,
    )

    # Add RawContextMiddleware
    app.add_middleware(RawContextMiddleware)

    # Register routes
    register_routes(app)

    return app


@app.get("/")
def health_check() -> dict:
    return {"status": "ok", "service": "museum-guide-backend"}


@app.websocket("/analyze")
async def analyze_websocket(ws: WebSocket) -> None:
    """
    顶层定义的 WebSocket 路由，路径固定为 /analyze。
    复用 routers.analyze._handle_analyze_websocket 的核心逻辑。
    """
    await _handle_analyze_websocket(ws)


# Initialize app with middleware
get_app()
