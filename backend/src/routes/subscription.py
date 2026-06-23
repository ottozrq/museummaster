import datetime as dt
import logging
from typing import Any, Dict, Literal

from fastapi import Body, Depends, HTTPException

import sql_models as sm
from src.routes import TAG, MuseumDb, app, d
from utils.appstore_server_notifications import process_appstore_notification_body
from utils.subscription import (
    PRO_PERIOD_SCAN_LIMIT,
    SCAN_PACK_DEFAULT_TOTAL,
    apply_scan_pack_purchase,
    compute_pro_activation_expires_at_ts,
    first_quota_reset_ts_from_anchor_utc,
    get_quota_remaining,
    is_pro_crossgrade,
    preserved_scan_pack_fields_for_pro_upgrade,
    should_skip_duplicate_pro_activation,
    subscription_dict_after_activate_free_plan,
)

PlanType = Literal["free", "scan_pack", "pro_monthly", "pro_yearly"]

GOOGLE_PLAY_PACKAGE_NAME = "com.ottozhang.artiou"
GOOGLE_PLAY_PRODUCT_IDS: dict[str, str] = {
    "scan_pack": "com.ottozhang.artiou.iap.scan",
    "pro_monthly": "com.ottozhang.artiou.sub.scan.pro.monthly",
    "pro_yearly": "com.ottozhang.artiou.sub.scan.pro.yearly",
}

logger = logging.getLogger(__name__)


def _get_user_subscription(extras: Any) -> dict[str, Any]:
    if not isinstance(extras, dict):
        return {}
    sub = extras.get("subscription")
    return sub if isinstance(sub, dict) else {}


def _clean_str(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _current_quota_response(user: sm.User, db: MuseumDb, now: dt.datetime) -> Dict[str, Any]:
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
        "pro_next_quota_reset_ts": sub_after.get("pro_next_quota_reset_ts"),
    }


def _google_payload_present(payload: Dict[str, Any]) -> bool:
    return any(
        _clean_str(payload.get(key))
        for key in (
            "google_purchase_token",
            "google_order_id",
            "google_product_id",
            "google_package_name",
        )
    )


def _validate_google_purchase_shape(plan_type: PlanType, payload: Dict[str, Any]) -> None:
    if not _google_payload_present(payload):
        return
    if plan_type == "free":
        raise HTTPException(status_code=400, detail="Google purchase cannot activate free plan")

    incoming_token = _clean_str(payload.get("google_purchase_token"))
    product_id = _clean_str(payload.get("google_product_id"))
    package_name = _clean_str(payload.get("google_package_name"))
    expected_product = GOOGLE_PLAY_PRODUCT_IDS.get(plan_type)
    if not incoming_token:
        raise HTTPException(status_code=400, detail="google_purchase_token is required")
    if product_id != expected_product:
        raise HTTPException(status_code=400, detail="Google product does not match plan_type")
    if package_name != GOOGLE_PLAY_PACKAGE_NAME:
        raise HTTPException(status_code=400, detail="Invalid Google package name")


def _google_purchase_token_used_by_other_user(
    db: MuseumDb,
    current_user: sm.User,
    payload: Dict[str, Any],
) -> bool:
    incoming_token = _clean_str(payload.get("google_purchase_token"))
    incoming_order = _clean_str(payload.get("google_order_id"))
    if not incoming_token and not incoming_order:
        return False

    current_user_id = getattr(current_user, "user_id", None)
    for existing_user in db.session.query(sm.User).filter(sm.User.extras.isnot(None)):
        if getattr(existing_user, "user_id", None) == current_user_id:
            continue
        sub = _get_user_subscription(getattr(existing_user, "extras", None))
        if _is_duplicate_google_purchase(sub, payload):
            return True
    return False


def _is_duplicate_google_purchase(prev_sub: dict[str, Any], payload: Dict[str, Any]) -> bool:
    incoming_token = _clean_str(payload.get("google_purchase_token"))
    incoming_order = _clean_str(payload.get("google_order_id"))
    if not incoming_token and not incoming_order:
        return False

    seen_tokens = prev_sub.get("google_purchase_tokens")
    if isinstance(seen_tokens, list) and incoming_token:
        if incoming_token in {str(x) for x in seen_tokens}:
            return True

    seen_orders = prev_sub.get("google_order_ids")
    if isinstance(seen_orders, list) and incoming_order:
        if incoming_order in {str(x) for x in seen_orders}:
            return True

    return (
        (incoming_token and incoming_token == _clean_str(prev_sub.get("google_purchase_token")))
        or (incoming_order and incoming_order == _clean_str(prev_sub.get("google_order_id")))
    )


def _append_google_purchase_fields(sub: dict[str, Any], payload: Dict[str, Any]) -> dict[str, Any]:
    out = dict(sub)
    incoming_token = _clean_str(payload.get("google_purchase_token"))
    incoming_order = _clean_str(payload.get("google_order_id"))
    product_id = _clean_str(payload.get("google_product_id"))
    package_name = _clean_str(payload.get("google_package_name"))
    if incoming_token:
        tokens = [str(x) for x in out.get("google_purchase_tokens", []) if str(x).strip()] if isinstance(out.get("google_purchase_tokens"), list) else []
        if incoming_token not in tokens:
            tokens.append(incoming_token)
        out["google_purchase_tokens"] = tokens[-20:]
        out["google_purchase_token"] = incoming_token
    if incoming_order:
        orders = [str(x) for x in out.get("google_order_ids", []) if str(x).strip()] if isinstance(out.get("google_order_ids"), list) else []
        if incoming_order not in orders:
            orders.append(incoming_order)
        out["google_order_ids"] = orders[-20:]
        out["google_order_id"] = incoming_order
    if product_id:
        out["google_product_id"] = product_id
    if package_name:
        out["google_package_name"] = package_name
    return out


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
        # Pro 月度额度下次重置（UTC 次月同日 0:00），Unix 秒
        "pro_next_quota_reset_ts": sub.get("pro_next_quota_reset_ts"),
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
    _validate_google_purchase_shape(plan_type, payload)
    if _google_purchase_token_used_by_other_user(db, user, payload):
        raise HTTPException(status_code=409, detail="Google purchase already used")

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
        if _is_duplicate_google_purchase(prev_sub, payload):
            logger.info(
                "subscription activate skipped duplicate google scan_pack user_id=%s",
                getattr(user, "user_id", None),
            )
            return _current_quota_response(user, db, now)
        add = int(payload.get("scan_pack_remaining") or SCAN_PACK_DEFAULT_TOTAL)
        if add <= 0:
            raise HTTPException(
                status_code=400, detail="scan_pack_remaining must be > 0"
            )
        extras["subscription"] = _append_google_purchase_fields(
            apply_scan_pack_purchase(prev_sub, add, now),
            payload,
        )
    else:
        prev_sub = _get_user_subscription(extras)
        if _is_duplicate_google_purchase(prev_sub, payload):
            logger.info(
                "subscription activate skipped duplicate google pro grant user_id=%s plan=%s",
                getattr(user, "user_id", None),
                plan_type,
            )
            return _current_quota_response(user, db, now)
        if should_skip_duplicate_pro_activation(
            prev_sub,
            plan_type,
            payload.get("apple_transaction_id"),
            now,
        ):
            logger.info(
                "subscription activate skipped duplicate pro grant user_id=%s plan=%s",
                getattr(user, "user_id", None),
                plan_type,
            )
            return _current_quota_response(user, db, now)

        expires_ts = compute_pro_activation_expires_at_ts(prev_sub, plan_type, now)
        scan_total = PRO_PERIOD_SCAN_LIMIT
        preserved_pack = preserved_scan_pack_fields_for_pro_upgrade(prev_sub)

        if is_pro_crossgrade(prev_sub, plan_type, now):
            pt = prev_sub.get("pro_scan_total")
            pr = prev_sub.get("pro_scan_remaining")
            pt_i = (
                int(pt)
                if isinstance(pt, (int, float)) and float(pt) > 0
                else PRO_PERIOD_SCAN_LIMIT
            )
            pr_i = (
                int(pr)
                if isinstance(pr, (int, float)) and float(pr) >= 0
                else PRO_PERIOD_SCAN_LIMIT
            )
            pt_i = min(pt_i, PRO_PERIOD_SCAN_LIMIT)
            pr_i = min(pr_i, pt_i)
            nxt_raw = prev_sub.get("pro_next_quota_reset_ts")
            nxt = (
                int(nxt_raw)
                if isinstance(nxt_raw, (int, float))
                else first_quota_reset_ts_from_anchor_utc(now)
            )
            merged = {
                "type": plan_type,
                "pro_expires_at_ts": expires_ts,
                "pro_scan_total": pt_i,
                "pro_scan_remaining": pr_i,
                "pro_next_quota_reset_ts": nxt,
                **preserved_pack,
            }
        else:
            merged = {
                "type": plan_type,
                "pro_expires_at_ts": expires_ts,
                "pro_scan_total": scan_total,
                "pro_scan_remaining": scan_total,
                "pro_next_quota_reset_ts": first_quota_reset_ts_from_anchor_utc(now),
                **preserved_pack,
            }
        otid = payload.get("apple_original_transaction_id")
        if otid:
            merged["apple_original_transaction_id"] = str(otid)
        tid = payload.get("apple_transaction_id")
        if tid:
            merged["apple_transaction_id"] = str(tid)
        extras["subscription"] = _append_google_purchase_fields(merged, payload)

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
        "pro_next_quota_reset_ts": sub_after.get("pro_next_quota_reset_ts"),
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
