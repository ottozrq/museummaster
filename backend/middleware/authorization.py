import starlette_context
from casbin.enforcer import Enforcer
from starlette import status
from starlette.authentication import BaseUser
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from utils import flags


class CasbinMiddleware:
    """
    Middleware for Casbin
    from https://github.com/pycasbin/fastapi-authz
    """

    def __init__(
        self,
        app: ASGIApp,
        enforcer: Enforcer,
    ) -> None:
        """
        Configure Casbin Middleware
        :param app:Retain for ASGI.
        :param enforcer:Casbin Enforcer, must be initialized before FastAPI start.
        """
        self.app = app
        self.enforcer = enforcer

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            # WebSocket: skip Casbin (Request is HTTP-only); allow through
            if scope["type"] == "websocket":
                await self.app(scope, receive, send)
                return
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return

            # 一些明确的“公开接口”即使 AuthenticationMiddleware 未注入 user，
            # 也应允许进入路由处理（路由自身会决定是否需要登录）。
            request = Request(scope, receive)
            path = request.url.path
            root_path = flags.MuseumFlags.get().root_path
            if root_path:
                root_path = str(root_path)
                if path.startswith(root_path):
                    path = path[len(root_path) :]
            normalized_path = (path or "").rstrip("/") or "/"
            # 公开接口兜底：直接放行到路由层，让路由决定是否需要登录。
            if (
                normalized_path
                in {
                    "/analyze",
                    "/tts",
                    "/auth",
                    "/docs",
                    "/openapi.json",
                    "/redoc",
                    "/subscription/appstore-notifications",
                }
                or normalized_path.startswith("/static/")
                or normalized_path.startswith("/analyze/")
            ):
                await self.app(scope, receive, send)
                return

            if await self._enforce(scope, receive):
                await self.app(scope, receive, send)
                return
            request = Request(scope, receive)
            if request.user.is_authenticated:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Unauthorized")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
        except HTTPException as e:
            await JSONResponse(
                status_code=e.status_code,
                content=dict(detail=e.detail),
            )(scope, receive, send)

    async def _enforce(self, scope: Scope, receive: Receive) -> bool:
        """
        Enforce a request
        :param user: user will be sent to enforcer
        :param request: ASGI Request
        :return: Enforce Result
        """
        request = Request(scope, receive)
        path = request.url.path
        root_path = flags.MuseumFlags.get().root_path
        if root_path:
            root_path = str(root_path)
            if path.startswith(root_path):
                prefix_length = len(root_path)
                path = path[prefix_length:]
        method = request.method
        if "user" not in scope:
            raise RuntimeError(
                "Casbin Middleware must work with an Authentication Middleware"
            )
        # 某些“无需认证但受 Casbin 保护”的 public endpoint，
        # AuthenticationMiddleware 可能不会提供有效的 request.user。
        # 此时仍应以匿名角色继续走 enforcer.enforce，
        # 让 policy 决定是否放行，而不是直接抛 401。
        if not request.user:
            role = "anonymous"
        else:
            assert isinstance(request.user, BaseUser)
            role = (
                request.user.role_string
                if request.user.is_authenticated
                else "anonymous"
            )
        starlette_context._enforcer = self.enforcer
        starlette_context.context["_enforcer_cache"] = {}
        starlette_context.context["user_role"] = role
        return self.enforcer.enforce(role, path, method)
