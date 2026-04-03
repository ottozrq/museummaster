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
    apply_scan_pack_purchase,
    consume_quota_after_success,
    get_quota_remaining,
    merge_scan_pack_into_active_pro_subscription,
    preserved_scan_pack_fields_for_pro_upgrade,
    subscription_dict_after_activate_free_plan,
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


def test_merge_scan_pack_into_pro_adds_on_top_of_pro_quota():
    """Pro 有效时购买加量包：在既有 scan pack 剩余上累加，且 get_quota 仍为 pro 计划。"""
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    prev = {
        "type": "pro_monthly",
        "pro_expires_at_ts": expires,
        "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
        "pro_scan_remaining": 100,
        "scan_pack_total": 50,
        "scan_pack_remaining": 10,
    }
    merged = merge_scan_pack_into_active_pro_subscription(prev, 50, now)
    assert merged is not None
    assert merged["type"] == "pro_monthly"
    assert merged["pro_scan_remaining"] == 100
    assert merged["scan_pack_total"] == 100
    assert merged["scan_pack_remaining"] == 60

    user = SimpleNamespace(extras={"subscription": merged})
    q = get_quota_remaining(user, None, now=now)
    assert q["plan"] == "pro_monthly"
    assert q["remaining"] == 160
    assert q["limit"] == PRO_MONTHLY_SCAN_LIMIT + 100


def test_merge_scan_pack_first_purchase_while_on_pro():
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    prev = {
        "type": "pro_yearly",
        "pro_expires_at_ts": expires,
        "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT * 12,
        "pro_scan_remaining": 200,
    }
    merged = merge_scan_pack_into_active_pro_subscription(prev, 50, now)
    assert merged is not None
    assert merged["scan_pack_remaining"] == 50
    assert merged["scan_pack_total"] == 50


def test_merge_scan_pack_returns_none_without_pro():
    assert (
        merge_scan_pack_into_active_pro_subscription({"type": "scan_pack"}, 50) is None
    )


def test_apply_scan_pack_standalone_stacks_multiple_purchases():
    """无 Pro 时多次购买加量包：remaining/total 累加写入。"""
    now = dt.datetime.now(dt.timezone.utc)
    first = apply_scan_pack_purchase({}, 50, now)
    assert first["type"] == "scan_pack"
    assert first["scan_pack_remaining"] == 50
    assert first["scan_pack_total"] == 50

    second = apply_scan_pack_purchase(first, 50, now)
    assert second["scan_pack_remaining"] == 100
    assert second["scan_pack_total"] == 100


def test_activate_free_plan_preserves_pro_and_pack_remaining():
    """前端选择免费：Pro 剩余与加量包剩余合并为 scan_pack。"""
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    prev = {
        "type": "pro_monthly",
        "pro_expires_at_ts": expires,
        "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
        "pro_scan_remaining": 120,
        "scan_pack_total": 50,
        "scan_pack_remaining": 20,
    }
    out = subscription_dict_after_activate_free_plan(prev, now)
    assert out is not None
    assert out["type"] == "scan_pack"
    assert out["scan_pack_remaining"] == 140
    assert out["scan_pack_total"] == 140


def test_activate_free_plan_preserves_scan_pack_only():
    now = dt.datetime.now(dt.timezone.utc)
    prev = {
        "type": "scan_pack",
        "scan_pack_total": 50,
        "scan_pack_remaining": 30,
    }
    out = subscription_dict_after_activate_free_plan(prev, now)
    assert out is not None
    assert out["scan_pack_remaining"] == 30


def test_activate_free_plan_returns_none_when_no_remaining():
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    assert (
        subscription_dict_after_activate_free_plan(
            {
                "type": "pro_monthly",
                "pro_expires_at_ts": expires,
                "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
                "pro_scan_remaining": 0,
                "scan_pack_remaining": 0,
            },
            now,
        )
        is None
    )


def test_apply_scan_pack_preserves_pro_fields():
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    prev = {
        "type": "pro_monthly",
        "pro_expires_at_ts": expires,
        "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
        "pro_scan_remaining": 88,
    }
    out = apply_scan_pack_purchase(prev, 50, now)
    assert out["type"] == "pro_monthly"
    assert out["pro_scan_remaining"] == 88
    assert out["pro_expires_at_ts"] == expires
    assert out["scan_pack_remaining"] == 50
    assert out["scan_pack_total"] == 50
