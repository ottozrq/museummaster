import datetime as dt
from typing import Any, Literal, TypedDict

from fastapi import HTTPException
from sqlalchemy import func

import sql_models as sm

PlanType = Literal["free", "scan_pack", "pro_monthly", "pro_yearly"]

# 图中规则：Free = 每日 5 次
FREE_DAILY_SCAN_LIMIT = 5

# 图中规则：Scan Pack = 50 次
SCAN_PACK_DEFAULT_TOTAL = 50

PRO_MONTHLY_DAYS = 30
PRO_YEARLY_DAYS = 365

# pro 扫描额度（每次 analyze 成功扣减 1）
PRO_MONTHLY_SCAN_LIMIT = 200
# 默认理解：年订也是“每月 200 次”，即一年 2400 次
PRO_YEARLY_SCAN_LIMIT = 200 * 12


class QuotaResponse(TypedDict):
    plan: PlanType
    limit: int
    used: int
    remaining: int
    # 额外信息：前端展示/调试用
    pro_expires_at_ts: int | None
    scan_pack_total: int | None


def preserved_scan_pack_fields_for_pro_upgrade(
    prev_sub: dict[str, Any]
) -> dict[str, Any]:
    """
    从当前 subscription 字典中取出升级到 Pro 时需保留的 scan pack 字段（若有剩余）。
    与 routes/subscription.activate_subscription 中 pro 分支行为一致。
    """
    preserved: dict[str, Any] = {}
    rem = prev_sub.get("scan_pack_remaining")
    if isinstance(rem, (int, float)) and float(rem) > 0:
        total_val = prev_sub.get("scan_pack_total")
        st = (
            int(total_val)
            if isinstance(total_val, (int, float)) and float(total_val) > 0
            else SCAN_PACK_DEFAULT_TOTAL
        )
        sr = min(int(rem), st)
        preserved["scan_pack_total"] = st
        preserved["scan_pack_remaining"] = sr
    return preserved


def _subscription_dict(extras: Any) -> dict[str, Any]:
    if not isinstance(extras, dict):
        return {}
    sub = extras.get("subscription")
    return sub if isinstance(sub, dict) else {}


def _now_utc(now: dt.datetime | None = None) -> dt.datetime:
    if now is not None:
        return now if now.tzinfo else now.replace(tzinfo=dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc)


def _is_pro_active(sub: dict[str, Any], now: dt.datetime) -> PlanType | None:
    pro_type = sub.get("type")
    if pro_type not in ("pro_monthly", "pro_yearly"):
        return None

    expires_ts = sub.get("pro_expires_at_ts")
    if not isinstance(expires_ts, (int, float)):
        return None

    # pro 过期则回退到 free
    if now.timestamp() >= float(expires_ts):
        return None
    return pro_type  # type: ignore[return-value]


def get_active_plan(user: sm.User, now: dt.datetime | None = None) -> PlanType:
    """
    根据 user.extras.subscription 判断当前激活订阅：
    - pro_*：pro_expires_at_ts 未过期 => pro
    - scan_pack：scan_pack_remaining > 0 => scan_pack
    - 其他 => free
    """
    now = _now_utc(now)
    sub = _subscription_dict(getattr(user, "extras", None))
    if pro_plan := _is_pro_active(sub, now):
        return pro_plan

    remaining = sub.get("scan_pack_remaining")
    if isinstance(remaining, (int, float)) and float(remaining) > 0:
        return "scan_pack"

    return "free"


def _daily_window(now: dt.datetime) -> tuple[dt.datetime, dt.datetime]:
    start = dt.datetime(now.year, now.month, now.day, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    return start, end


def get_quota_remaining(
    user: sm.User,
    db_session,
    now: dt.datetime | None = None,
) -> QuotaResponse:
    """
    返回当前用户的识别额度（UTC 口径：free 为每日统计，pro/scan_pack 为“剩余次数”统计）。
    """
    now = _now_utc(now)
    plan = get_active_plan(user, now=now)
    pro_expires_at_ts = None
    scan_pack_total = None

    sub = _subscription_dict(getattr(user, "extras", None))
    if plan == "free":
        start, end = _daily_window(now)
        user_id = str(user.user_id)
        used = (
            db_session.query(func.count(sm.ScanRecord.scan_id))
            .filter(
                sm.ScanRecord.user_id == user_id,
                sm.ScanRecord.inserted_at >= start,
                sm.ScanRecord.inserted_at < end,
            )
            .scalar()
            or 0
        )
        remaining = max(0, FREE_DAILY_SCAN_LIMIT - int(used))
        return QuotaResponse(
            plan="free",
            limit=FREE_DAILY_SCAN_LIMIT,
            used=int(used),
            remaining=int(remaining),
            pro_expires_at_ts=None,
            scan_pack_total=None,
        )

    if plan == "scan_pack":
        scan_pack_total_val = sub.get("scan_pack_total")
        scan_pack_remaining_val = sub.get("scan_pack_remaining")
        scan_pack_total = (
            scan_pack_total_val
            if isinstance(scan_pack_total_val, (int, float))
            and float(scan_pack_total_val) > 0
            else SCAN_PACK_DEFAULT_TOTAL
        )
        scan_pack_remaining = (
            scan_pack_remaining_val
            if isinstance(scan_pack_remaining_val, (int, float))
            and float(scan_pack_remaining_val) >= 0
            else 0
        )
        used = max(0, int(scan_pack_total) - int(scan_pack_remaining))
        return QuotaResponse(
            plan="scan_pack",
            limit=int(scan_pack_total),
            used=int(used),
            remaining=int(max(0, scan_pack_remaining)),
            pro_expires_at_ts=None,
            scan_pack_total=int(scan_pack_total),
        )

    # pro_*：按订阅周期限制次数
    pro_expires_at_ts = sub.get("pro_expires_at_ts")
    if not isinstance(pro_expires_at_ts, (int, float)):
        pro_expires_at_ts = None

    default_total = (
        PRO_MONTHLY_SCAN_LIMIT if plan == "pro_monthly" else PRO_YEARLY_SCAN_LIMIT
    )
    pro_scan_total_val = sub.get("pro_scan_total")
    pro_scan_remaining_val = sub.get("pro_scan_remaining")

    pro_scan_total = int(default_total)
    if isinstance(pro_scan_total_val, (int, float)) and pro_scan_total_val > 0:
        pro_scan_total = int(pro_scan_total_val)

    pro_scan_remaining = int(default_total)
    if isinstance(pro_scan_remaining_val, (int, float)) and pro_scan_remaining_val >= 0:
        pro_scan_remaining = int(pro_scan_remaining_val)
    # 防御：remaining 不能超过 total
    pro_scan_remaining = min(pro_scan_remaining, pro_scan_total)

    # 从 scan pack 升级到 pro 时保留的剩余次数，与订阅池叠加
    sp_total_val = sub.get("scan_pack_total")
    sp_rem_val = sub.get("scan_pack_remaining")
    pack_total = 0
    pack_remaining = 0
    if isinstance(sp_rem_val, (int, float)) and float(sp_rem_val) > 0:
        pack_remaining = int(sp_rem_val)
        if isinstance(sp_total_val, (int, float)) and float(sp_total_val) > 0:
            pack_total = int(sp_total_val)
        else:
            pack_total = pack_remaining
        pack_remaining = min(pack_remaining, pack_total)

    combined_limit = int(pro_scan_total) + int(pack_total)
    combined_remaining = int(pro_scan_remaining) + int(pack_remaining)
    combined_used = max(0, combined_limit - combined_remaining)

    return QuotaResponse(
        plan=plan,
        limit=int(combined_limit),
        used=int(combined_used),
        remaining=int(max(0, combined_remaining)),
        pro_expires_at_ts=(
            int(pro_expires_at_ts) if pro_expires_at_ts is not None else None
        ),
        scan_pack_total=int(pack_total) if pack_total > 0 else None,
    )


def _quota_exhausted_http(detail_code: str, message: str) -> HTTPException:
    # detail 用结构体，前端可以更可靠识别 code
    return HTTPException(
        status_code=429,
        detail={"code": detail_code, "message": message},
    )


def consume_quota_after_success(
    user: sm.User, db, now: dt.datetime | None = None
) -> None:
    """
    在一次 analyze 成功后调用：
    - free：再次检查今日剩余额度（避免并发导致超量）
    - scan_pack：扣减 scan_pack_remaining（并发使用 SELECT ... FOR UPDATE）
    - pro：扣减 pro_scan_remaining
    """
    now = _now_utc(now)
    plan = get_active_plan(user, now=now)

    if plan == "pro_monthly" or plan == "pro_yearly":
        # 并发下强一致扣减：只扣减 1 次；先扣订阅池，再扣升级 pro 时保留的 scan pack
        user_id = str(user.user_id)
        locked = (
            db.session.query(sm.User)
            .filter(sm.User.user_id == user_id)
            .with_for_update()
            .one()
        )
        current_extras = getattr(locked, "extras", None)
        extras_dict = current_extras if isinstance(current_extras, dict) else {}
        sub = _subscription_dict(extras_dict)

        default_total = (
            PRO_MONTHLY_SCAN_LIMIT if plan == "pro_monthly" else PRO_YEARLY_SCAN_LIMIT
        )
        total_val = sub.get("pro_scan_total")
        remaining_val = sub.get("pro_scan_remaining")

        total = (
            int(total_val)
            if isinstance(total_val, (int, float)) and total_val > 0
            else int(default_total)
        )
        remaining = (
            int(remaining_val)
            if isinstance(remaining_val, (int, float)) and remaining_val >= 0
            else int(total)
        )

        new_sub = dict(sub)

        if remaining > 0:
            new_sub["pro_scan_total"] = total
            new_sub["pro_scan_remaining"] = int(remaining) - 1
        else:
            sp_rem = sub.get("scan_pack_remaining")
            if isinstance(sp_rem, (int, float)) and int(sp_rem) > 0:
                new_sub["scan_pack_remaining"] = int(sp_rem) - 1
            else:
                raise _quota_exhausted_http(
                    detail_code="PRO_QUOTA_EXCEEDED",
                    message="Pro scan quota exhausted.",
                )

        new_extras = dict(extras_dict)
        new_extras["subscription"] = new_sub
        locked.extras = new_extras
        db.session.add(locked)
        return

    if plan == "free":
        start, end = _daily_window(now)
        user_id = str(user.user_id)
        used = (
            db.session.query(func.count(sm.ScanRecord.scan_id))
            .filter(
                sm.ScanRecord.user_id == user_id,
                sm.ScanRecord.inserted_at >= start,
                sm.ScanRecord.inserted_at < end,
            )
            .scalar()
            or 0
        )
        if int(used) >= FREE_DAILY_SCAN_LIMIT:
            raise _quota_exhausted_http(
                detail_code="DAILY_SCAN_QUOTA_EXCEEDED",
                message=("Daily scan quota exceeded. Please try again tomorrow."),
            )
        return

    # scan_pack
    # 这里需要强一致：一次 analyze 成功只扣减 1 次
    user_id = str(user.user_id)
    locked = (
        db.session.query(sm.User)
        .filter(sm.User.user_id == user_id)
        .with_for_update()
        .one()
    )
    current_extras = getattr(locked, "extras", None)
    extras_dict = current_extras if isinstance(current_extras, dict) else {}
    sub = _subscription_dict(extras_dict)
    remaining = sub.get("scan_pack_remaining")
    if not isinstance(remaining, (int, float)) or float(remaining) <= 0:
        raise _quota_exhausted_http(
            detail_code="SCAN_PACK_QUOTA_EXCEEDED",
            message="Scan pack quota exhausted.",
        )

    new_sub = dict(sub)
    new_sub["scan_pack_remaining"] = int(remaining) - 1
    new_extras = dict(extras_dict)
    new_extras["subscription"] = new_sub
    locked.extras = new_extras
    db.session.add(locked)
