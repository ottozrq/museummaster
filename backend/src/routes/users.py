from datetime import datetime, timedelta

import jwt
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from passlib.context import CryptContext

import depends as d
from src.routes import TAG, Depends, HTTPException, app, m, sm, status
from utils import flags
from utils.utils import MuseumDb

VF = flags.MuseumFlags.get()

ACCESS_TOKEN_EXPIRE_DAYS = 1
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@app.post("/token/", tags=[TAG.Root], response_model=m.LoginResponse)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: MuseumDb = Depends(d.get_psql),
):
    try:
        user = m.User.db(db).query.filter_by(user_email=form_data.username).first()
        if not pwd_context.verify(form_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
        return m.LoginResponse(
            access_token=jwt.encode(
                {
                    "user_id": user.user_id,
                    "role": user.role,
                    "exp": datetime.now() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
                },
                VF.login_secret,
                algorithm="HS256",
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e.__class__.__name__),
        )


@app.post("/register/", tags=[TAG.Root], response_model=m.User)
def register(
    user: m.UserCreate,
    db: MuseumDb = Depends(d.get_psql),
):
    if m.User.db(db).query.filter_by(user_email=user.user_email).first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"email already registered: {user.user_email}",
        )

    user_db = sm.User(
        user_email=user.user_email,
        password=pwd_context.hash(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        extras=user.extras,
    )
    db.session.add(user_db)
    db.session.commit()
    return m.User.from_db(user_db)


class ResetPasswordResponse(m.Model):
    success: bool = True


class ResetPasswordRequest(m.Model):
    old_password: str
    new_password: str


class DeleteAccountResponse(m.Model):
    success: bool = True


@app.post(
    "/reset_password/",
    response_model=ResetPasswordResponse,
    tags=[TAG.Users],
)
def reset_user_password(
    rest_password_form: ResetPasswordRequest,
    db: MuseumDb = Depends(d.get_psql),
    user: sm.User = Depends(d.get_logged_in_user),
):
    if not pwd_context.verify(rest_password_form.old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    user.password = pwd_context.hash(rest_password_form.new_password)
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return ResetPasswordResponse()


@app.get(
    "/user/",
    response_model=m.User,
    tags=[TAG.Users],
)
def user(
    user: sm.User = Depends(d.get_logged_in_user),
):
    return m.User.from_db(user)


@app.delete(
    "/users/me",
    response_model=DeleteAccountResponse,
    tags=[TAG.Users],
)
def delete_my_account(
    db: MuseumDb = Depends(d.get_psql),
    user: sm.User = Depends(d.get_logged_in_user),
):
    """
    永久删除当前登录账号，用于满足平台账号删除合规要求。
    """
    db.session.delete(user)
    db.session.commit()
    return DeleteAccountResponse()
