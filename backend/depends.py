import logging
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import PositiveInt, StringConstraints
from typing_extensions import Annotated

import models as m
import sql_models as sm
from utils import flags
from utils.utils import MuseumDb, postgres_session


class _Bearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        return not flags.MuseumFlags.get().superuser_email and await super(
            _Bearer, self
        ).__call__(request)


security = _Bearer("/token/")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_psql() -> MuseumDb:
    with postgres_session() as psql:
        yield psql


def get_pagination(
    request: Request,
    page_token: Optional[
        Annotated[str, StringConstraints(pattern=r"\d+")]
    ] = None,
    page_size: PositiveInt = None,
):
    return m.Pagination(
        request=request,
        page_size=page_size,
        page_token=page_token,
    )


def get_user_id(
    request: Request,
    _=Depends(security),
) -> str:
    return str(request.user.user_uuid)


def get_user_email(
    request: Request,
    _=Depends(security),
) -> str:
    return str(request.user.user_email)


def get_logged_in_user(
    user_id=Depends(get_user_id),
    db=Depends(get_psql),
) -> sm.User:
    return m.User.db(db).get_or_404(user_id)


def get_optional_logged_in_user(
    request: Request,
    db: MuseumDb = Depends(get_psql),
) -> Optional[sm.User]:
    user_uuid = getattr(getattr(request, "user", None), "user_uuid", None)
    if not user_uuid:
        return None
    try:
        return m.User.db(db).get_or_none(user_uuid)
    except Exception:
        logger.debug("optional user lookup failed", exc_info=True)
        return None


def superuser_email() -> str:
    return flags.MuseumFlags.get().superuser_email
