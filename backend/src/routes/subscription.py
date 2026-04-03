import datetime as dt
import logging
from typing import Any, Dict, Literal

from fastapi import Body, Depends, HTTPException

import sql_models as sm
from src.routes import TAG, MuseumDb, app, d
from utils.appstore_server_notifications import process_appstore_notification_body
from utils.subscription import (
    PRO_MONTHLY_DAYS,
    PRO_MONTHLY_SCAN_LIMIT,
    PRO_YEARLY_DAYS,
    PRO_YEARLY_SCAN_LIMIT,
    SCAN_PACK_DEFAULT_TOTAL,
    apply_scan_pack_purchase,
    get_quota_remaining,
    preserved_scan_pack_fields_for_pro_upgrade,
    subscription_dict_after_activate_free_plan,
)

PlanType = Literal["free", "scan_pack", "pro_monthly", "pro_yearly"]

logger = logging.getLogger(__name__)


def _get_user_subscription(extras: Any) -> dict[str, Any]:
    if not isinstance(extras, dict):
        return {}
    sub = extras.get("subscription")
    return sub if isinstance(sub, dict) else {}


@app.get("/subscription/current", tags=[TAG.Analyze])
def get_subscription_current(
    user: sm.User = Depends(d.get_logged_in_user),
    db: MuseumDb = Depends(d.get_psql),
) -> Dict[str, Any]:
    """
    返回当前订阅与额度。
    """
    now = dt.datetime.now(dt.timezone.utc)
    quota = get_quota_remaining(user, db.session, now=now)
    sub = _get_user_subscription(getattr(user, "extras", None))
    return {
        "plan": quota["plan"],
        "limit": quota["limit"],
        "used": quota["used"],
        "remaining": quota["remaining"],
        "pro_expires_at_ts": (
            quota["pro_expires_at_ts"] or sub.get("pro_expires_at_ts")
        ),
        "scan_pack_total": quota["scan_pack_total"],
        "scan_pack_remaining": sub.get("scan_pack_remaining"),
        "daily_limit": quota.get("limit") if quota["plan"] == "free" else None,
        # App Store Server Notifications 同步：1=将自动续费 0=已关闭自动续费 None=未知
        "apple_auto_renew_status": sub.get("apple_auto_renew_status"),
        "apple_original_transaction_id": sub.get("apple_original_transaction_id"),
    }


@app.post("/subscription/activate", tags=[TAG.Analyze])
def activate_subscription(
    payload: Dict[str, Any],
    user: sm.User = Depends(d.get_logged_in_user),
    db: MuseumDb = Depends(d.get_psql),
) -> Dict[str, Any]:
    """
    订阅激活（开发/内测用）：
    - 真实场景应由 Apple/Google 支付回调调用
    - 写入 user.extras.subscription：Pro 与 Scan Pack 可同时存在；加量包多次购买会累加额度。
    """
    plan_type = payload.get("plan_type")
    if plan_type not in ("free", "scan_pack", "pro_monthly", "pro_yearly"):
        raise HTTPException(status_code=400, detail="Invalid plan_type")

    now = dt.datetime.now(dt.timezone.utc)
    extras = dict(getattr(user, "extras", None) or {})
    if "subscription" in extras and not isinstance(extras["subscription"], dict):
        extras.pop("subscription", None)

    if plan_type == "free":
        prev_sub = _get_user_subscription(extras)
        new_sub = subscription_dict_after_activate_free_plan(prev_sub, now)
        if new_sub is None:
            extras.pop("subscription", None)
        else:
            extras["subscription"] = new_sub
    elif plan_type == "scan_pack":
        prev_sub = _get_user_subscription(extras)
        add = int(payload.get("scan_pack_remaining") or SCAN_PACK_DEFAULT_TOTAL)
        if add <= 0:
            raise HTTPException(
                status_code=400, detail="scan_pack_remaining must be > 0"
            )
        extras["subscription"] = apply_scan_pack_purchase(prev_sub, add, now)
    else:
        days = PRO_MONTHLY_DAYS if plan_type == "pro_monthly" else PRO_YEARLY_DAYS
        expires_ts = int((now + dt.timedelta(days=days)).timestamp())
        scan_total = (
            PRO_MONTHLY_SCAN_LIMIT
            if plan_type == "pro_monthly"
            else PRO_YEARLY_SCAN_LIMIT
        )
        prev_sub = _get_user_subscription(extras)
        preserved_pack = preserved_scan_pack_fields_for_pro_upgrade(prev_sub)

        merged: dict[str, Any] = {
            "type": plan_type,
            "pro_expires_at_ts": expires_ts,
            "pro_scan_total": scan_total,
            "pro_scan_remaining": scan_total,
            **preserved_pack,
        }
        otid = payload.get("apple_original_transaction_id")
        if otid:
            merged["apple_original_transaction_id"] = str(otid)
        tid = payload.get("apple_transaction_id")
        if tid:
            merged["apple_transaction_id"] = str(tid)
        extras["subscription"] = merged

    user.extras = extras
    db.session.add(user)
    db.session.commit()

    quota = get_quota_remaining(user, db.session, now=now)
    sub_after = _get_user_subscription(getattr(user, "extras", None))
    return {
        "plan": quota["plan"],
        "limit": quota["limit"],
        "used": quota["used"],
        "remaining": quota["remaining"],
        "pro_expires_at_ts": quota["pro_expires_at_ts"],
        "scan_pack_total": quota["scan_pack_total"],
        "scan_pack_remaining": sub_after.get("scan_pack_remaining"),
    }


@app.post("/subscription/appstore-notifications", tags=[TAG.Analyze])
def appstore_server_notifications(
    payload: Dict[str, Any] = Body(...),
    db: MuseumDb = Depends(d.get_psql),
) -> Dict[str, Any]:
    """
    App Store Server Notifications v2 入口（无需登录）。
    在 App Store Connect → App → 综合 → App 内购买项目 → 服务器通知 中配置生产/沙盒 URL。

    客户端开通 Pro 时须上报 apple_original_transaction_id，否则无法将通知关联到用户。
    """
    try:
        ok = process_appstore_notification_body(payload, db.session)
        if ok:
            db.session.commit()
        else:
            db.session.rollback()
    except Exception:
        logger.exception("appstore notification handler failed")
        db.session.rollback()
        ok = False
    # Apple 要求尽快返回 200；解析失败也返回 200，避免无限重试淹没日志
    return {"ok": ok}


__all__ = [
    "get_subscription_current",
    "activate_subscription",
    "appstore_server_notifications",
]
