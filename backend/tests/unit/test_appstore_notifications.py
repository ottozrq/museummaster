"""App Store Server Notifications 解析与 extras 更新逻辑。"""

import datetime as dt

import jwt

from utils.appstore_server_notifications import (
    apply_notification_to_user_subscription,
    parse_notification_request_body,
)


def test_parse_notification_request_body_minimal():
    inner_tx = jwt.encode(
        {"originalTransactionId": "1000000123", "expiresDate": 2000000000000},
        "secret",
        algorithm="HS256",
    )
    body = {
        "signedPayload": jwt.encode(
            {
                "notificationType": "DID_CHANGE_RENEWAL_STATUS",
                "subtype": "AUTO_RENEW_DISABLED",
                "data": {
                    "signedTransactionInfo": inner_tx,
                    "signedRenewalInfo": jwt.encode(
                        {"autoRenewStatus": 0}, "secret", algorithm="HS256"
                    ),
                },
            },
            "secret",
            algorithm="HS256",
        )
    }
    nt, sub, tx, renewal = parse_notification_request_body(body)
    assert nt == "DID_CHANGE_RENEWAL_STATUS"
    assert sub == "AUTO_RENEW_DISABLED"
    assert tx.get("originalTransactionId") == "1000000123"
    assert renewal.get("autoRenewStatus") == 0


def test_apply_did_change_renewal_status():
    now = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    extras: dict = {
        "subscription": {
            "type": "pro_monthly",
            "pro_expires_at_ts": 2000000000,
            "apple_original_transaction_id": "1000000123",
        }
    }
    out = apply_notification_to_user_subscription(
        extras,
        "DID_CHANGE_RENEWAL_STATUS",
        "AUTO_RENEW_DISABLED",
        {"originalTransactionId": "1000000123"},
        {"autoRenewStatus": 0},
        now,
    )
    assert out["subscription"]["apple_auto_renew_status"] == 0


def test_apply_expired_sets_expires():
    now = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    expires_ms = int(now.timestamp() * 1000)
    extras: dict = {
        "subscription": {"type": "pro_monthly", "pro_expires_at_ts": 2000000000}
    }
    out = apply_notification_to_user_subscription(
        extras,
        "EXPIRED",
        None,
        {"originalTransactionId": "x", "expiresDate": expires_ms},
        {},
        now,
    )
    assert out["subscription"]["pro_expires_at_ts"] == int(now.timestamp())
