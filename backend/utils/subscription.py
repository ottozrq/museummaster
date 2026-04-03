import calendar
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

# Pro：月订 / 年订均为「每自然月周期」200 次（UTC：次月同一日历日 00:00 重置），非年订一次性 2400
PRO_PERIOD_SCAN_LIMIT = 200
PRO_MONTHLY_SCAN_LIMIT = PRO_PERIOD_SCAN_LIMIT
# 兼容旧引用：与 PRO_PERIOD_SCAN_LIMIT 相同（不再表示年度总池）
PRO_YEARLY_SCAN_LIMIT = PRO_PERIOD_SCAN_LIMIT


class QuotaResponse(TypedDict):
    plan: PlanType
    limit: int
    used: int
    remaining: int
    # 额外信息：前端展示/调试用
    pro_expires_at_ts: int | None
    scan_pack_total: int | None


def add_calendar_months(d: dt.date, months: int) -> dt.date:
    """日历月加法（如 1/31 + 1 月 → 2/28 或 2/29）。"""
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    last = calendar.monthrange(y, m)[1]
    day = min(d.day, last)
    return dt.date(y, m, day)


def first_quota_reset_ts_from_anchor_utc(anchor: dt.datetime) -> int:
    """以 anchor 的 UTC 日历日为锚，次月同一日 00:00:00 UTC 为下一次重置时刻。"""
    a = anchor if anchor.tzinfo else anchor.replace(tzinfo=dt.timezone.utc)
    next_d = add_calendar_months(a.date(), 1)
    reset = dt.datetime.combine(next_d, dt.time.min, tzinfo=dt.timezone.utc)
    return int(reset.timestamp())


def apply_pro_period_resets_to_dict(
    sub: dict[str, Any], now: dt.datetime
) -> tuple[dict[str, Any], bool]:
    """
    Pro 月订/年订：跨过 pro_next_quota_reset_ts（UTC 次月同日 0 点）则重置为每周期 PRO_PERIOD_SCAN_LIMIT。
    处理旧数据（无 next_ts、年订一次性大额 total）迁移。
    返回 (新 subscription 字典, 是否修改)。
    """
    now = _now_utc(now)
    if sub.get("type") not in ("pro_monthly", "pro_yearly"):
        return sub, False
    exp = sub.get("pro_expires_at_ts")
    if not isinstance(exp, (int, float)):
        return sub, False
    if now.timestamp() >= float(exp):
        return sub, False

    out = dict(sub)
    changed = False

    nxt_raw = out.get("pro_next_quota_reset_ts")
    pt = out.get("pro_scan_total")

    if not isinstance(nxt_raw, (int, float)):
        if isinstance(pt, (int, float)) and int(pt) > PRO_PERIOD_SCAN_LIMIT:
            pr = out.get("pro_scan_remaining")
            pr_i = (
                int(pr)
                if isinstance(pr, (int, float)) and float(pr) >= 0
                else PRO_PERIOD_SCAN_LIMIT
            )
            out["pro_scan_total"] = PRO_PERIOD_SCAN_LIMIT
            out["pro_scan_remaining"] = min(pr_i, PRO_PERIOD_SCAN_LIMIT)
        out["pro_next_quota_reset_ts"] = first_quota_reset_ts_from_anchor_utc(now)
        changed = True
    elif isinstance(pt, (int, float)) and int(pt) > PRO_PERIOD_SCAN_LIMIT:
        pr = out.get("pro_scan_remaining")
        pr_i = (
            int(pr)
            if isinstance(pr, (int, float)) and float(pr) >= 0
            else PRO_PERIOD_SCAN_LIMIT
        )
        out["pro_scan_total"] = PRO_PERIOD_SCAN_LIMIT
        out["pro_scan_remaining"] = min(pr_i, PRO_PERIOD_SCAN_LIMIT)
        changed = True

    exp_f = float(exp)
    while True:
        nxt_v = out.get("pro_next_quota_reset_ts")
        if not isinstance(nxt_v, (int, float)):
            break
        nxt_f = float(nxt_v)
        if now.timestamp() < nxt_f:
            break
        if nxt_f >= exp_f:
            break
        out["pro_scan_total"] = PRO_PERIOD_SCAN_LIMIT
        out["pro_scan_remaining"] = PRO_PERIOD_SCAN_LIMIT
        reset_dt = dt.datetime.fromtimestamp(nxt_f, tz=dt.timezone.utc)
        next_d = add_calendar_months(reset_dt.date(), 1)
        next_reset = dt.datetime.combine(next_d, dt.time.min, tzinfo=dt.timezone.utc)
        new_nxt = int(next_reset.timestamp())
        out["pro_next_quota_reset_ts"] = new_nxt
        changed = True

    return out, changed


def is_pro_crossgrade(
    prev_sub: dict[str, Any],
    plan_type: str,
    now: dt.datetime,
) -> bool:
    """
    是否为「未过期的月订 ↔ 年订」切换：新套餐时长从当前 Pro 周期结束时刻起算（而非立即从 now 起算）。
    """
    now = _now_utc(now)
    if plan_type not in ("pro_monthly", "pro_yearly"):
        return False
    prev_type = prev_sub.get("type")
    if prev_type not in ("pro_monthly", "pro_yearly") or prev_type == plan_type:
        return False
    exp = prev_sub.get("pro_expires_at_ts")
    if not isinstance(exp, (int, float)):
        return False
    return now.timestamp() < float(exp)


def compute_pro_activation_expires_at_ts(
    prev_sub: dict[str, Any],
    plan_type: str,
    now: dt.datetime,
) -> int:
    """
    写入新 Pro 时的 pro_expires_at_ts（Unix 秒）：
    - 月↔年跨档且当前周期未结束：当前周期结束时间 + 新套餐天数（年订 +365 天、月订 +30 天）；
    - 否则：now + 新套餐天数。
    """
    now = _now_utc(now)
    days = PRO_MONTHLY_DAYS if plan_type == "pro_monthly" else PRO_YEARLY_DAYS
    if is_pro_crossgrade(prev_sub, plan_type, now):
        exp = prev_sub.get("pro_expires_at_ts")
        if not isinstance(exp, (int, float)):
            return int((now + dt.timedelta(days=days)).timestamp())
        anchor_end = dt.datetime.fromtimestamp(float(exp), tz=dt.timezone.utc)
        return int((anchor_end + dt.timedelta(days=days)).timestamp())
    return int((now + dt.timedelta(days=days)).timestamp())


def refresh_pro_monthly_quota_if_due(
    user: sm.User,
    db_session,
    now: dt.datetime | None = None,
) -> None:
    """在读额度或扣减前调用：若跨过重置日则写回 extras（有 db 时 commit）。"""
    now = _now_utc(now)
    extras = getattr(user, "extras", None) or {}
    sub = _subscription_dict(extras)
    if not _is_pro_active(sub, now):
        return
    new_sub, changed = apply_pro_period_resets_to_dict(sub, now)
    if not changed:
        return
    new_extras = dict(extras)
    new_extras["subscription"] = new_sub
    user.extras = new_extras
    if db_session is not None:
        db_session.add(user)
        db_session.commit()


def subscription_dict_after_activate_free_plan(
    prev_sub: dict[str, Any],
    now: dt.datetime | None = None,
) -> dict[str, Any] | None:
    """
    用户在前端选择「免费」同步到后端时：不再保留 Pro 订阅，但将 Pro 池与加量包池的剩余次数合并为
    type=scan_pack，避免取消订阅后清空账户内剩余识别次数。
    若合并后无可保留次数，返回 None（表示可清除 subscription）。
    """
    now = _now_utc(now)
    if not prev_sub:
        return None

    pack_rem = 0
    sp_rem = prev_sub.get("scan_pack_remaining")
    if isinstance(sp_rem, (int, float)) and float(sp_rem) > 0:
        pack_rem = int(sp_rem)
        sp_total = prev_sub.get("scan_pack_total")
        cap = (
            int(sp_total)
            if isinstance(sp_total, (int, float)) and float(sp_total) > 0
            else pack_rem
        )
        pack_rem = min(pack_rem, cap)

    pro_type = prev_sub.get("type")
    pro_rem = 0
    if pro_type in ("pro_monthly", "pro_yearly"):
        default_total = PRO_PERIOD_SCAN_LIMIT
        pt = prev_sub.get("pro_scan_total")
        pr_total = (
            int(pt)
            if isinstance(pt, (int, float)) and float(pt) > 0
            else int(default_total)
        )
        pr_val = prev_sub.get("pro_scan_remaining")
        pr_rem = (
            int(pr_val)
            if isinstance(pr_val, (int, float)) and float(pr_val) >= 0
            else int(pr_total)
        )
        pr_rem = min(max(0, pr_rem), pr_total)
        # 未过期 / 已过期 Pro 均保留 pro_scan_remaining
        pro_rem = pr_rem

    total_remaining = pro_rem + pack_rem
    if total_remaining <= 0:
        return None

    out: dict[str, Any] = {
        "type": "scan_pack",
        "scan_pack_total": int(total_remaining),
        "scan_pack_remaining": int(total_remaining),
    }
    # 保留 Apple 交易标识，便于 Pro 再次 activate 时与同一笔 IAP 去重（避免取消后反复刷额度）
    otid = prev_sub.get("apple_original_transaction_id")
    if otid:
        out["apple_original_transaction_id"] = str(otid)
    atid = prev_sub.get("apple_transaction_id")
    if atid:
        out["apple_transaction_id"] = str(atid)
    return out


def _norm_apple_txn_id(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def should_skip_duplicate_pro_activation(
    prev_sub: dict[str, Any],
    plan_type: str,
    incoming_tid: Any,
    now: dt.datetime | None = None,
) -> bool:
    """
    Pro 激活是否应跳过写入（不重复发放额度）：
    - 请求中的 apple_transaction_id 与已存储的相同 → 同一笔 IAP（含取消后仍为 scan_pack
      但保留了上次 Pro 的 transaction id），不重复发放；
    - 未带 transaction_id 但当前已是同方案且未过期的 Pro → 客户端重复请求。
    新交易 ID 时返回 False，正常发放。
    """
    if plan_type not in ("pro_monthly", "pro_yearly"):
        return False
    now = _now_utc(now)
    incoming = _norm_apple_txn_id(incoming_tid)
    stored = _norm_apple_txn_id(prev_sub.get("apple_transaction_id"))

    if incoming and stored and incoming == stored:
        return True

    if incoming:
        return False

    if prev_sub.get("type") != plan_type:
        return False
    exp = prev_sub.get("pro_expires_at_ts")
    if not isinstance(exp, (int, float)):
        return False
    return now.timestamp() < float(exp)


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


def merge_scan_pack_into_active_pro_subscription(
    prev_sub: dict[str, Any],
    add: int,
    now: dt.datetime | None = None,
) -> dict[str, Any] | None:
    """
    未过期 Pro：将本次加量包 add 次累加到 scan_pack_remaining / scan_pack_total。
    非 Pro：返回 None，由路由写入独立 scan_pack 订阅。
    """
    now = _now_utc(now)
    pro_type = _is_pro_active(prev_sub, now)
    if pro_type is None:
        return None
    if add <= 0:
        return None
    prev_rem = prev_sub.get("scan_pack_remaining")
    prev_total = prev_sub.get("scan_pack_total")
    base_rem = (
        int(prev_rem)
        if isinstance(prev_rem, (int, float)) and float(prev_rem) > 0
        else 0
    )
    base_total = (
        int(prev_total)
        if isinstance(prev_total, (int, float)) and float(prev_total) > 0
        else 0
    )
    new_rem = base_rem + int(add)
    new_total = base_total + int(add)
    out = dict(prev_sub)
    out["type"] = pro_type
    out["scan_pack_remaining"] = new_rem
    out["scan_pack_total"] = new_total
    return out


def apply_scan_pack_purchase(
    prev_sub: dict[str, Any],
    add: int,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """
    一次加量包购买后应写入的 subscription 字典（持久化在 user.extras）：
    - 有效 Pro：保留 pro_expires_at_ts、pro_scan_*，并累加 scan_pack_*；
    - 仅 scan_pack：多次购买累加 remaining/total；
    - 否则：新建 type=scan_pack（首购）。
    """
    now = _now_utc(now)
    pro_merged = merge_scan_pack_into_active_pro_subscription(prev_sub, add, now)
    if pro_merged is not None:
        return pro_merged

    if prev_sub.get("type") == "scan_pack":
        prev_rem = prev_sub.get("scan_pack_remaining")
        prev_total = prev_sub.get("scan_pack_total")
        base_rem = (
            int(prev_rem)
            if isinstance(prev_rem, (int, float)) and float(prev_rem) >= 0
            else 0
        )
        base_total = (
            int(prev_total)
            if isinstance(prev_total, (int, float)) and float(prev_total) > 0
            else 0
        )
        new_rem = base_rem + int(add)
        new_total = base_total + int(add)
        return {
            "type": "scan_pack",
            "scan_pack_total": new_total,
            "scan_pack_remaining": new_rem,
        }

    total = int(SCAN_PACK_DEFAULT_TOTAL)
    rem = int(add)
    if rem > total:
        rem = total
    return {
        "type": "scan_pack",
        "scan_pack_total": total,
        "scan_pack_remaining": rem,
    }


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

    if plan in ("pro_monthly", "pro_yearly"):
        refresh_pro_monthly_quota_if_due(user, db_session, now=now)
        sub = _subscription_dict(getattr(user, "extras", None))

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

    default_total = PRO_PERIOD_SCAN_LIMIT
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
        sub, reset_changed = apply_pro_period_resets_to_dict(sub, now)
        if reset_changed:
            extras_dict = dict(extras_dict)
            extras_dict["subscription"] = sub
            locked.extras = extras_dict

        default_total = PRO_PERIOD_SCAN_LIMIT
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
