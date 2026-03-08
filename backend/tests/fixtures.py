from datetime import datetime

from passlib.context import CryptContext

# import models as m
import sql_models as sm

from .sqlalchemy_fixture_factory.sqla_fix_fact import (  # subFactoryGet,; subFactoryModel,
    BaseFix,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseFix):
    MODEL = sm.User
    user_email = "otto@example.com"
    password = pwd_context.hash("666666")
    first_name = "Otto"
    last_name = "Zhang"
    date_joined = datetime(1970, 1, 1)
    extras = {}
