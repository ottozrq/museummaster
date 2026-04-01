import datetime as dt
from typing import Any, Dict, Literal

from fastapi import Depends, HTTPException

import sql_models as sm
from src.routes import TAG, MuseumDb, app, d
from utils.subscription import (
    PRO_MONTHLY_DAYS,
    PRO_YEARLY_DAYS,
    SCAN_PACK_DEFAULT_TOTAL,
    get_quota_remaining,
)

PlanType = Literal["free", "scan_pack", "pro_monthly", "pro_yearly"]


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
        "pro_expires_at_ts": quota["pro_expires_at_ts"] or sub.get("pro_expires_at_ts"),
        "scan_pack_total": quota["scan_pack_total"],
        "scan_pack_remaining": sub.get("scan_pack_remaining"),
        "daily_limit": quota.get("limit") if quota["plan"] == "free" else None,
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
    - 这里只更新 user.extras，供前端联调“额度规则”
    """
    plan_type = payload.get("plan_type")
    if plan_type not in ("free", "scan_pack", "pro_monthly", "pro_yearly"):
        raise HTTPException(status_code=400, detail="Invalid plan_type")

    now = dt.datetime.now(dt.timezone.utc)
    extras = dict(getattr(user, "extras", None) or {})
    if "subscription" in extras and not isinstance(extras["subscription"], dict):
        extras.pop("subscription", None)

    if plan_type == "free":
        extras.pop("subscription", None)
    elif plan_type == "scan_pack":
        extras["subscription"] = {
            "type": "scan_pack",
            "scan_pack_total": SCAN_PACK_DEFAULT_TOTAL,
            "scan_pack_remaining": int(
                payload.get("scan_pack_remaining") or SCAN_PACK_DEFAULT_TOTAL
            ),
        }
        if extras["subscription"]["scan_pack_remaining"] <= 0:
            raise HTTPException(
                status_code=400, detail="scan_pack_remaining must be > 0"
            )
        if int(extras["subscription"]["scan_pack_remaining"]) > int(
            extras["subscription"]["scan_pack_total"]
        ):
            extras["subscription"]["scan_pack_remaining"] = int(
                extras["subscription"]["scan_pack_total"]
            )
    else:
        days = PRO_MONTHLY_DAYS if plan_type == "pro_monthly" else PRO_YEARLY_DAYS
        expires_ts = int((now + dt.timedelta(days=days)).timestamp())
        extras["subscription"] = {
            "type": plan_type,
            "pro_expires_at_ts": expires_ts,
        }

    user.extras = extras
    db.session.add(user)
    db.session.commit()

    quota = get_quota_remaining(user, db.session, now=now)
    return {
        "plan": quota["plan"],
        "limit": quota["limit"],
        "used": quota["used"],
        "remaining": quota["remaining"],
        "pro_expires_at_ts": quota["pro_expires_at_ts"],
        "scan_pack_total": quota["scan_pack_total"],
    }


__all__ = ["get_subscription_current", "activate_subscription"]
