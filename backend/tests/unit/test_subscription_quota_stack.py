"""Scan Pack 升级到 Pro 后额度叠加与扣减顺序的单元测试。"""

import datetime as dt
import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import sql_models as sm
from utils.subscription import (
    PRO_MONTHLY_DAYS,
    PRO_MONTHLY_SCAN_LIMIT,
    PRO_YEARLY_DAYS,
    apply_pro_period_resets_to_dict,
    apply_scan_pack_purchase,
    compute_pro_activation_expires_at_ts,
    consume_quota_after_success,
    get_quota_remaining,
    is_pro_crossgrade,
    merge_scan_pack_into_active_pro_subscription,
    preserved_scan_pack_fields_for_pro_upgrade,
    should_skip_duplicate_pro_activation,
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
        "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
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


def test_activate_free_plan_preserves_apple_transaction_ids():
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    prev = {
        "type": "pro_monthly",
        "pro_expires_at_ts": expires,
        "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
        "pro_scan_remaining": 10,
        "apple_original_transaction_id": "orig-1",
        "apple_transaction_id": "tx-99",
    }
    out = subscription_dict_after_activate_free_plan(prev, now)
    assert out is not None
    assert out["apple_original_transaction_id"] == "orig-1"
    assert out["apple_transaction_id"] == "tx-99"


def test_skip_duplicate_pro_same_apple_transaction_id():
    """同一 apple_transaction_id 重复激活：跳过重复发放。"""
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    prev = {
        "type": "pro_monthly",
        "pro_expires_at_ts": expires,
        "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
        "pro_scan_remaining": 50,
        "apple_transaction_id": "1001",
    }
    assert (
        should_skip_duplicate_pro_activation(prev, "pro_monthly", "1001", now) is True
    )


def test_skip_duplicate_pro_no_tid_but_still_active():
    """无 transaction_id 时，已是未过期同方案 Pro：重复请求不重复发放。"""
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    prev = {
        "type": "pro_monthly",
        "pro_expires_at_ts": expires,
        "pro_scan_total": PRO_MONTHLY_SCAN_LIMIT,
        "pro_scan_remaining": 10,
    }
    assert should_skip_duplicate_pro_activation(prev, "pro_monthly", None, now) is True


def test_no_skip_pro_new_transaction_id():
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    prev = {
        "type": "pro_monthly",
        "pro_expires_at_ts": expires,
        "apple_transaction_id": "1001",
        "pro_scan_remaining": 10,
    }
    assert (
        should_skip_duplicate_pro_activation(prev, "pro_monthly", "1002", now) is False
    )


def test_no_skip_pro_from_scan_pack():
    """从加量包升 Pro：无 stored tid，不视为重复。"""
    now = dt.datetime.now(dt.timezone.utc)
    prev = {
        "type": "scan_pack",
        "scan_pack_total": 50,
        "scan_pack_remaining": 30,
    }
    assert (
        should_skip_duplicate_pro_activation(prev, "pro_monthly", "1001", now) is False
    )


def test_skip_pro_after_cancel_scan_pack_keeps_same_apple_transaction_id():
    """取消 Pro 后 scan_pack 仍带 apple_transaction_id，用同一 id 再激活 Pro → 不重复发放。"""
    now = dt.datetime.now(dt.timezone.utc)
    prev = {
        "type": "scan_pack",
        "scan_pack_total": 140,
        "scan_pack_remaining": 140,
        "apple_transaction_id": "9001",
    }
    assert should_skip_duplicate_pro_activation(prev, "pro_yearly", "9001", now) is True


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


def test_pro_period_resets_at_next_month_same_calendar_day_utc():
    """跨过 pro_next_quota_reset_ts 后重置为 200，下一锚点为次月同日 0:00 UTC。"""
    now = dt.datetime(2026, 3, 15, 14, 0, 0, tzinfo=dt.timezone.utc)
    expires = int(dt.datetime(2027, 1, 1, tzinfo=dt.timezone.utc).timestamp())
    nxt = int(dt.datetime(2026, 3, 15, 0, 0, 0, tzinfo=dt.timezone.utc).timestamp())
    sub = {
        "type": "pro_monthly",
        "pro_expires_at_ts": expires,
        "pro_scan_total": 200,
        "pro_scan_remaining": 3,
        "pro_next_quota_reset_ts": nxt,
    }
    new_sub, changed = apply_pro_period_resets_to_dict(sub, now)
    assert changed
    assert new_sub["pro_scan_remaining"] == 200
    apr15 = dt.datetime(2026, 4, 15, 0, 0, 0, tzinfo=dt.timezone.utc)
    assert new_sub["pro_next_quota_reset_ts"] == int(apr15.timestamp())


def test_legacy_yearly_lump_clamped_to_period_limit():
    """旧版年订一次性 total=2400 迁移为每周期 200 上限。"""
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    sub = {
        "type": "pro_yearly",
        "pro_expires_at_ts": expires,
        "pro_scan_total": 2400,
        "pro_scan_remaining": 500,
    }
    new_sub, changed = apply_pro_period_resets_to_dict(sub, now)
    assert changed
    assert new_sub["pro_scan_total"] == PRO_MONTHLY_SCAN_LIMIT
    assert new_sub["pro_scan_remaining"] == min(500, PRO_MONTHLY_SCAN_LIMIT)


def test_crossgrade_monthly_to_yearly_expires_from_monthly_end():
    """月订未结束时改年订：年周期从「当前月订结束」起 +365 天。"""
    now = dt.datetime(2026, 1, 10, 12, 0, 0, tzinfo=dt.timezone.utc)
    monthly_end = dt.datetime(2026, 2, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    prev = {
        "type": "pro_monthly",
        "pro_expires_at_ts": int(monthly_end.timestamp()),
    }
    assert is_pro_crossgrade(prev, "pro_yearly", now) is True
    exp = compute_pro_activation_expires_at_ts(prev, "pro_yearly", now)
    want_end = monthly_end + timedelta(days=PRO_YEARLY_DAYS)
    assert exp == int(want_end.timestamp())


def test_crossgrade_yearly_to_monthly_expires_from_yearly_end():
    """年订未结束时改月订：新月周期从「当前年订结束」起 +30 天。"""
    now = dt.datetime(2026, 1, 10, tzinfo=dt.timezone.utc)
    yearly_end = dt.datetime(2026, 12, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    prev = {
        "type": "pro_yearly",
        "pro_expires_at_ts": int(yearly_end.timestamp()),
    }
    assert is_pro_crossgrade(prev, "pro_monthly", now) is True
    exp = compute_pro_activation_expires_at_ts(prev, "pro_monthly", now)
    want_end = yearly_end + timedelta(days=PRO_MONTHLY_DAYS)
    assert exp == int(want_end.timestamp())


def test_same_pro_plan_not_crossgrade():
    now = dt.datetime.now(dt.timezone.utc)
    expires = _future_expires_ts(now)
    prev = {"type": "pro_monthly", "pro_expires_at_ts": expires}
    assert is_pro_crossgrade(prev, "pro_monthly", now) is False


def test_crossgrade_false_when_previous_pro_expired():
    now = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    prev = {
        "type": "pro_monthly",
        "pro_expires_at_ts": int(
            dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).timestamp()
        ),
    }
    assert is_pro_crossgrade(prev, "pro_yearly", now) is False


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
