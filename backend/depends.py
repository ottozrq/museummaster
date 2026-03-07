import logging
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from middleware.authentication import MuseumAuthUser
from utils import flags


class _Bearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        return not flags.MuseumFlags.get().superuser_email and await super(
            _Bearer, self
        ).__call__(request)


security = _Bearer("/token/")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_user_id(
    request: Request,
    _=Depends(security),
) -> str:
    return str(request.user.user_uuid)


def get_user_email(
    request: Request,
    _=Depends(security),
) -> str:
    return str(request.user.email)


def get_logged_in_user(
    user_id=Depends(get_user_id),
) -> Optional[MuseumAuthUser]:
    """获取当前登录用户"""
    return request.user if hasattr(request, "user") else None


def get_logged_in_user_or_none(
    request: Request = None,
) -> Optional[MuseumAuthUser]:
    """获取当前登录用户，如果未登录则返回None"""
    try:
        if hasattr(request, "user") and request.user:
            return request.user
    except Exception:
        pass
    return None


def superuser_email() -> str:
    return flags.MuseumFlags.get().superuser_email
