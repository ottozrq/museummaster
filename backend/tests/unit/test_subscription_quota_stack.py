"""Scan Pack 升级到 Pro 后额度叠加与扣减顺序的单元测试。"""

import datetime as dt
import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import sql_models as sm
from utils.subscription import (
    PRO_MONTHLY_SCAN_LIMIT,
    consume_quota_after_success,
    get_quota_remaining,
    preserved_scan_pack_fields_for_pro_upgrade,
)


def _future_expires_ts(now, days: int = 40) -> int:
    return int((now + timedelta(days=days)).timestamp())


def _mock_db_returning_user(locked_user: sm.User) -> MagicMock:
    """consume_quota_after_success 内会 query User 并 with_for_update。"""
    mock_db = MagicMock()
    chain = MagicMock()
    chain.filter.return_value.with_for_update.return_value.one.return_value = (
        locked_user
    )
    mock_db.session.query.return_value = chain
    return mock_db


@pytest.mark.parametrize(
    "pro_rem,pack_rem,expected_total_rem,expected_limit",
    [
        (100, 20, 120, PRO_MONTHLY_SCAN_LIMIT + 50),
        (200, 0, 200, PRO_MONTHLY_SCAN_LIMIT),
        (0, 15, 15, PRO_MONTHLY_SCAN_LIMIT + 50),
    ],
)
def test_get_quota_remaining_pro_stacks_scan_pack(
    pro_rem, pack_rem, expected_total_rem, expected_limit
):
    """Pro 与保留的 scan pack 额度在 remaining/limit 上叠加。"""
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    user = SimpleNamespace(
        extras={
            "subscription": {
                "type": "pro_monthly",
                "pro_expires_at_ts": expires,
                "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
                "pro_scan_remaining": pro_rem,
                "scan_pack_total": 50,
                "scan_pack_remaining": pack_rem,
            }
        }
    )
    q = get_quota_remaining(user, None, now=now)
    assert q["plan"] == "pro_monthly"
    assert q["remaining"] == expected_total_rem
    assert q["limit"] == expected_limit
    assert q["used"] == q["limit"] - q["remaining"]
    if pack_rem > 0:
        assert q["scan_pack_total"] == 50
    else:
        assert q["scan_pack_total"] is None


def test_consume_quota_deducts_pro_before_scan_pack():
    """先扣 pro_scan_remaining，为 0 后再扣 scan_pack_remaining。"""
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    uid = uuid.UUID("00000000-0000-0000-0000-000000000099")
    user = sm.User(
        user_id=uid,
        user_email="stack-test-pro@example.com",
        password="x",
        first_name="",
        last_name="",
    )
    user.extras = {
        "subscription": {
            "type": "pro_monthly",
            "pro_expires_at_ts": expires,
            "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
            "pro_scan_remaining": 10,
            "scan_pack_total": 50,
            "scan_pack_remaining": 5,
        }
    }
    mock_db = _mock_db_returning_user(user)

    consume_quota_after_success(user, mock_db, now=now)

    sub = user.extras.get("subscription") or {}
    assert sub["pro_scan_remaining"] == 9
    assert sub["scan_pack_remaining"] == 5


def test_consume_quota_uses_scan_pack_when_pro_exhausted():
    """pro_scan_remaining 为 0 时扣 scan_pack。"""
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    uid = uuid.UUID("00000000-0000-0000-0000-000000000098")
    user = sm.User(
        user_id=uid,
        user_email="stack-test-pack@example.com",
        password="x",
        first_name="",
        last_name="",
    )
    user.extras = {
        "subscription": {
            "type": "pro_monthly",
            "pro_expires_at_ts": expires,
            "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
            "pro_scan_remaining": 0,
            "scan_pack_total": 50,
            "scan_pack_remaining": 3,
        }
    }
    mock_db = _mock_db_returning_user(user)

    consume_quota_after_success(user, mock_db, now=now)

    sub = user.extras.get("subscription") or {}
    assert sub["pro_scan_remaining"] == 0
    assert sub["scan_pack_remaining"] == 2


def test_preserved_scan_pack_fields_for_pro_upgrade():
    """preserved_scan_pack_fields_for_pro_upgrade 与 activate 中 pro 升级合并一致。"""
    prev_sub = {
        "type": "scan_pack",
        "scan_pack_total": 50,
        "scan_pack_remaining": 30,
    }
    preserved_pack = preserved_scan_pack_fields_for_pro_upgrade(prev_sub)
    assert preserved_pack == {"scan_pack_total": 50, "scan_pack_remaining": 30}

    merged = {
        "type": "pro_monthly",
        "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
        "pro_scan_remaining": PRO_MONTHLY_SCAN_LIMIT,
        **preserved_pack,
    }
    assert merged["scan_pack_remaining"] == 30
    assert merged["pro_scan_remaining"] == PRO_MONTHLY_SCAN_LIMIT


def test_preserved_scan_pack_empty_when_no_remaining():
    assert (
        preserved_scan_pack_fields_for_pro_upgrade(
            {"type": "scan_pack", "scan_pack_total": 50, "scan_pack_remaining": 0}
        )
        == {}
    )
