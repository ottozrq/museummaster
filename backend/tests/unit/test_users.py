from src.routes.users import ResetPasswordRequest, ResetPasswordResponse
from tests import ApiClient, m, sm, status


def test_register(cl: ApiClient):
    user_email = "otto"
    user = m.User.from_response(
        cl(
            "/register/",
            method="POST",
            data=m.UserCreate(
                user_email=user_email,
                password="666666",
            ),
        )
    )
    assert user.user_email == user_email


def test_token(cl: ApiClient, user_admin: sm.User):
    cl(
        "/token/",
        method="POST",
        data={"password": "wrong", "username": "otto@ottozhang.com"},
        as_dict=True,
        status=status.HTTP_401_UNAUTHORIZED,
    )
    assert (
        m.LoginResponse.from_response(
            cl(
                "/token/",
                method="POST",
                data={"password": "666666", "username": "otto@ottozhang.com"},
                as_dict=True,
            )
        ).token_type
        == "bearer"
    )


def test_reset_password(cl: ApiClient):
    cl.logout()
    cl(
        "/reset_password",
        method="POST",
        data=ResetPasswordRequest(
            old_password="111",
            new_password="222",
        ),
        status=status.HTTP_401_UNAUTHORIZED,
    )
    cl.login()
    cl(
        "/reset_password",
        method="POST",
        data=ResetPasswordRequest(
            old_password="111",
            new_password="222",
        ),
        status=status.HTTP_401_UNAUTHORIZED,
    )
    assert ResetPasswordResponse.from_response(
        cl(
            "/reset_password",
            method="POST",
            data=ResetPasswordRequest(
                old_password="666666",
                new_password="111111",
            ),
        )
    ) == ResetPasswordResponse(success=True)


def test_user(cl: ApiClient, user_admin: sm.User):
    assert m.User.from_response(cl("user")) == m.User.from_db(user_admin)
