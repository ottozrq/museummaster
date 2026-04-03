"""
App Store Server Notifications v2：解析 Apple 推送，同步订阅续订/过期/关闭自动续费 等状态。

说明：
- signedPayload / 内层 JWS 默认仅做解码（verify_signature=False），生产环境建议改用
  Apple 官方 app-store-server-library 校验签名，或部署前在 App Store Connect 配置 URL 后
  用沙盒通知验证。
- 依赖客户端在开通 Pro 时上报 apple_original_transaction_id，以便按 originalTransactionId 关联用户。
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

import jwt

import sql_models as sm
from utils.subscription import (
    PRO_PERIOD_SCAN_LIMIT,
    first_quota_reset_ts_from_anchor_utc,
)

logger = logging.getLogger(__name__)


def decode_jws_payload_unverified(jws: str | None) -> dict[str, Any]:
    """解码 App Store JWS（不校验签名，仅解析 payload）。"""
    if not jws or not isinstance(jws, str):
        return {}
    try:
        # Apple 使用 ES256 等算法；关闭校验仅用于取出 claims
        decoded = jwt.decode(
            jws,
            algorithms=["ES256", "RS256", "HS256"],
            options={"verify_signature": False},
        )
        return dict(decoded) if isinstance(decoded, dict) else {}
    except jwt.exceptions.PyJWTError as e:
        logger.warning("appstore jws decode failed: %s", e)
        return {}


def parse_notification_request_body(
    body: dict[str, Any]
) -> tuple[str, str | None, dict, dict]:
    """
    从 POST JSON（含 signedPayload）解析 notificationType、subtype、transactionInfo、renewalInfo。
    """
    signed_payload = body.get("signedPayload")
    if not signed_payload:
        return "", None, {}, {}

    outer = decode_jws_payload_unverified(
        signed_payload if isinstance(signed_payload, str) else str(signed_payload)
    )
    notification_type = str(outer.get("notificationType") or "")
    subtype = outer.get("subtype")
    subtype_s = str(subtype) if subtype is not None else None

    data = outer.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    st = data.get("signedTransactionInfo")
    sr = data.get("signedRenewalInfo")

    tx = decode_jws_payload_unverified(st if isinstance(st, str) else None)
    renewal = decode_jws_payload_unverified(sr if isinstance(sr, str) else None)

    return notification_type, subtype_s, tx, renewal


def _ms_to_ts(expires_ms: Any) -> int | None:
    if expires_ms is None:
        return None
    try:
        ms = float(expires_ms)
        return int(ms / 1000.0)
    except (TypeError, ValueError):
        return None


def apply_notification_to_user_subscription(
    user_extras: dict[str, Any],
    notification_type: str,
    subtype: str | None,
    transaction_info: dict[str, Any],
    renewal_info: dict[str, Any],
    now: dt.datetime,
) -> dict[str, Any]:
    """
    根据通知更新 extras['subscription']，返回新的 extras 字典（浅拷贝写入）。
    """
    extras = dict(user_extras or {})
    sub = dict(extras.get("subscription") or {})

    expires_ts = _ms_to_ts(transaction_info.get("expiresDate"))
    original_id = transaction_info.get("originalTransactionId")
    if original_id is not None:
        sub["apple_original_transaction_id"] = str(original_id)
    tid = transaction_info.get("transactionId")
    if tid is not None:
        sub["apple_last_transaction_id"] = str(tid)

    if renewal_info:
        ars = renewal_info.get("autoRenewStatus")
        if ars is not None:
            try:
                sub["apple_auto_renew_status"] = int(ars)
            except (TypeError, ValueError):
                pass
        arp_ms = renewal_info.get("autoRenewProductId") or renewal_info.get(
            "autoRenewPreference"
        )
        if arp_ms is not None:
            sub["apple_auto_renew_product_id"] = str(arp_ms)

    now_ts = int(now.timestamp())

    if notification_type == "DID_CHANGE_RENEWAL_STATUS":
        # 用户关闭/打开自动续费；权益仍到当前周期结束
        sub["apple_renewal_status_updated_at_ts"] = now_ts
        logger.info(
            "apple DID_CHANGE_RENEWAL_STATUS subtype=%s autoRenew=%s",
            subtype,
            sub.get("apple_auto_renew_status"),
        )

    elif notification_type == "DID_RENEW":
        if expires_ts is not None and sub.get("type") in ("pro_monthly", "pro_yearly"):
            sub["pro_expires_at_ts"] = expires_ts
        sub["apple_last_renewal_at_ts"] = now_ts
        if sub.get("type") in ("pro_monthly", "pro_yearly"):
            sub["pro_scan_total"] = PRO_PERIOD_SCAN_LIMIT
            sub["pro_scan_remaining"] = PRO_PERIOD_SCAN_LIMIT
            pms = transaction_info.get("purchaseDate")
            if pms is not None:
                try:
                    ms = float(pms)
                    pdt = dt.datetime.fromtimestamp(ms / 1000.0, tz=dt.timezone.utc)
                    sub["pro_next_quota_reset_ts"] = (
                        first_quota_reset_ts_from_anchor_utc(pdt)
                    )
                except (TypeError, ValueError, OSError):
                    sub["pro_next_quota_reset_ts"] = (
                        first_quota_reset_ts_from_anchor_utc(now)
                    )
            else:
                sub["pro_next_quota_reset_ts"] = first_quota_reset_ts_from_anchor_utc(
                    now
                )

    elif notification_type in ("EXPIRED", "GRACE_PERIOD_EXPIRED"):
        sub["pro_expires_at_ts"] = expires_ts if expires_ts is not None else now_ts
        sub["apple_subscription_inactive_notified_at_ts"] = now_ts
        logger.info(
            "apple subscription end type=%s subtype=%s", notification_type, subtype
        )

    elif notification_type in ("REVOKE", "REFUND"):
        sub["pro_expires_at_ts"] = 0
        sub["apple_subscription_inactive_notified_at_ts"] = now_ts
        logger.info("apple subscription revoked/refund type=%s", notification_type)

    extras["subscription"] = sub
    return extras


def find_user_by_apple_original_transaction_id(session, otid: str) -> sm.User | None:
    """按 App Store originalTransactionId 查找用户（extras.subscription.apple_original_transaction_id）。"""
    otid = str(otid)
    try:
        u = (
            session.query(sm.User)
            .filter(
                sm.User.extras["subscription"]["apple_original_transaction_id"].astext
                == otid
            )
            .first()
        )
        if u is not None:
            return u
    except Exception as e:
        logger.debug("astext lookup failed: %s", e)

    for u in session.query(sm.User).filter(sm.User.extras.isnot(None)):
        sub = (u.extras or {}).get("subscription") or {}
        if str(sub.get("apple_original_transaction_id") or "") == otid:
            return u
    return None


def process_appstore_notification_body(body: dict[str, Any], session) -> bool:
    """
    处理一条 App Store Server Notification。成功写入用户则返回 True；
    无法关联用户或解析失败返回 False（仍建议 HTTP 200 避免 Apple 无限重试）。
    """
    notification_type, subtype, tx, renewal = parse_notification_request_body(body)
    if not notification_type:
        logger.warning("appstore notification: missing notificationType")
        return False
    otid = tx.get("originalTransactionId")
    if not otid:
        logger.warning("appstore notification: missing originalTransactionId")
        return False

    user = find_user_by_apple_original_transaction_id(session, str(otid))
    if user is None:
        logger.warning(
            "appstore notification: no user bound to originalTransactionId=%s", otid
        )
        return False

    now = dt.datetime.now(dt.timezone.utc)
    new_extras = apply_notification_to_user_subscription(
        getattr(user, "extras", None) or {},
        notification_type,
        subtype,
        tx,
        renewal,
        now,
    )
    user.extras = new_extras
    session.add(user)
    return True
