"""Artwork analysis: HTTP upload and WebSocket streaming."""

import asyncio
import base64
import datetime as dt
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import jwt
from fastapi import (
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from openai import AsyncOpenAI, OpenAI

import sql_models as sm
from src.routes import TAG, MuseumDb, app, d
from utils import flags
from utils.flags import GeminiFlags
from utils.subscription import (
    FREE_DAILY_SCAN_LIMIT,
    consume_quota_after_success,
    get_quota_remaining,
)
from utils.utils import postgres_session

IMAGE_DIR = Path("static") / "uploads" / "scans"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_FALLBACK_MODEL = "gemini-2.5-flash"


def _is_model_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "404" in message and (
        "not_found" in message
        or "no longer available" in message
        or "model" in message
        and "not found" in message
    )


def _is_admin_role(role: Any) -> bool:
    if role is None:
        return False
    # SQLAlchemy Enum returns sm.UserRole.* in normal cases.
    if role == sm.UserRole.admin:
        return True
    # Some drivers/config may return strings.
    role_name = getattr(role, "name", None)
    if isinstance(role_name, str) and role_name.lower() == "admin":
        return True
    if isinstance(role, str) and role.lower() == "admin":
        return True
    # Last resort: string representation.
    return str(role).lower().endswith(".admin") or str(role).lower() == "admin"


def _save_image_bytes(image_bytes: bytes, mime_type: str) -> str:
    ext = ".jpg"
    if mime_type.endswith("png"):
        ext = ".png"
    elif mime_type.endswith("jpeg"):
        ext = ".jpg"
    filename = f"scan_{uuid.uuid4().hex}{ext}"
    target_path = IMAGE_DIR / filename
    target_path.write_bytes(image_bytes)
    relative = target_path.relative_to("static")
    return f"/static/{relative.as_posix()}"


def _normalize_analyze_locale(tag: Optional[str]) -> str:
    """与前端 AppLanguage 对齐：zh / en / fr；未知或未提供时默认中文（兼容旧客户端）。"""
    if not tag or not str(tag).strip():
        return "zh"
    lower = str(tag).strip().lower().replace("_", "-")
    if lower.startswith("zh"):
        return "zh"
    if lower.startswith("fr"):
        return "fr"
    return "en"


def _locale_from_accept_language(header: Optional[str]) -> Optional[str]:
    if not header or not str(header).strip():
        return None
    first = str(header).split(",")[0].strip().split(";")[0].strip()
    return first or None


def _analyze_prompt(locale_code: str) -> str:
    if locale_code == "en":
        return (
            "You are a professional museum guide. Analyze this artwork image and "
            "write a detailed explanation in English. "
            "The response must include these sections, clearly separated, in concise language: "
            "1) Title of the work, 2) Artist, 3) Year or period, 4) Art style, "
            "5) Historical context, 6) Artistic significance. "
            "If information is uncertain, say it is possible or probable and give your reasoning. "
            "Do not output anything beyond these points; begin directly with the work title."
        )
    if locale_code == "fr":
        return (
            "Tu es un guide de musée professionnel. Analyse cette image d'œuvre d'art et "
            "rédige une explication détaillée en français. "
            "Le contenu doit inclure et structurer clairement les rubriques suivantes, "
            "dans un langage concis : "
            "1) Titre de l'œuvre, 2) Artiste, 3) Année ou période, 4) Style artistique, "
            "5) Contexte historique, 6) Importance artistique. "
            "Si une information est incertaine, indique explicitement que c'est "
            "« possible » ou « probable » et donne des éléments de justification. "
            "Ne produis rien d'autre que ces points ; commence directement par le titre de l'œuvre."
        )
    return (
        "你是一位专业的博物馆讲解员。请分析这张艺术品图片，并用中文输出详细讲解。"
        "内容必须包含并清晰分段，且用简洁的语言表达："
        "1) 作品标题，2) 艺术家，3) 创作年份，4) 艺术风格，"
        "5) 历史背景，6) 艺术意义。如果信息不确定，请明确说明‘可能’并给出依据。"
        "除了以上几点不要输出任何其他内容，介绍直接从作品标题开始。"
    )


@app.post("/analyze", tags=[TAG.Analyze])
async def analyze_artwork(
    request: Request,
    image: UploadFile = File(...),
    locale: Optional[str] = Form(None),
    db: MuseumDb = Depends(d.get_psql),
    user: Optional[sm.User] = Depends(d.get_optional_logged_in_user),
) -> Dict[str, str]:
    """
    非流式 analyze：接收图片，用 Gemini Responses API 生成讲解，返回 {"text": "..."}。
    """
    content_type = image.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image",
        )

    # 空文件校验必须放在 Gemini/额度逻辑之前，
    # 否则单测（空文件应返回 400）会先触发 GEMINI_API_KEY 缺失而返回 500。
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image is empty")

    gemini_flags = GeminiFlags.get()
    if not gemini_flags.api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set")
    user_id: Optional[str] = (
        str(user.user_id) if user and getattr(user, "user_id", None) else None
    )

    # 兜底：若 request.user 没解析出来（例如中间件未挂载/异常），
    # 则直接从 Authorization 头解析 user_id。
    #
    # 重要：如果客户端没有带 Authorization，则这是匿名可用的 /analyze
    # 逻辑，应允许继续执行（user_id 仍然保持 None）。
    auth_header = request.headers.get("Authorization")
    if user_id is None and auth_header:
        token = auth_header.strip()
        if token.lower().startswith("bearer "):
            token = token[len("bearer ") :].strip()
        try:
            payload = jwt.decode(
                token,
                flags.MuseumFlags.get().login_secret,
                algorithms=["HS256"],
            )
            raw_uuid = payload.get("user_id") or payload.get("user_uuid")
            if raw_uuid:
                user_id = str(raw_uuid)
        except Exception:
            # 带了 token 但解不出 user_id：按认证失败处理
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    # 如果客户端没带 Authorization，则 user_id 可能仍为 None（匿名）。

    # 已注册用户走订阅额度规则：Free / Scan Pack / Pro
    user_role = getattr(user, "role", None) if user else None
    if user_role is None and user_id:
        # 某些情况下 request.user 可能解析不到，但我们仍能从 user_id 回查角色。
        try:
            user_role = (
                db.session.query(sm.User.role)
                .filter(sm.User.user_id == user_id)
                .scalar()
            )
        except Exception:
            user_role = None

    user_db: sm.User | None = (
        user
        if user_id and user and getattr(user, "user_id", None) is not None
        else None
    )
    if user_db is None and user_id:
        user_db = (
            db.session.query(sm.User).filter(sm.User.user_id == user_id).one_or_none()
        )

    if user_db and not _is_admin_role(user_role):
        now = dt.datetime.now(dt.timezone.utc)
        quota = get_quota_remaining(user_db, db.session, now=now)
        if quota["remaining"] <= 0:
            plan = quota["plan"]
            if plan == "free":
                detail_code = "DAILY_SCAN_QUOTA_EXCEEDED"
                detail_message = "Daily scan quota exceeded. Please try again tomorrow."
            elif plan == "scan_pack":
                detail_code = "SCAN_PACK_QUOTA_EXCEEDED"
                detail_message = "Scan pack quota exhausted."
            elif plan in ("pro_monthly", "pro_yearly"):
                detail_code = "PRO_QUOTA_EXCEEDED"
                detail_message = "Pro scan quota exhausted."
            else:
                detail_code = "QUOTA_EXCEEDED"
                detail_message = "Quota exhausted."
            raise HTTPException(
                status_code=429,
                detail={
                    "code": detail_code,
                    "message": detail_message,
                },
            )

    # 保存原始图片到本地文件系统
    image_path = _save_image_bytes(image_bytes, content_type)

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:{content_type};base64,{image_b64}"
    client = OpenAI(api_key=gemini_flags.api_key, base_url=gemini_flags.base_url)
    model = gemini_flags.model

    lang_tag = locale or _locale_from_accept_language(
        request.headers.get("Accept-Language")
    )
    prompt_text = _analyze_prompt(_normalize_analyze_locale(lang_tag))

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
    except Exception as exc:
        if model != GEMINI_FALLBACK_MODEL and _is_model_not_found_error(exc):
            completion = client.chat.completions.create(
                model=GEMINI_FALLBACK_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
            )
        else:
            raise
    try:
        result_text = (
            (completion.choices[0].message.content or "")
            if getattr(completion, "choices", None)
            else ""
        )
        result_text = result_text.strip()
        if not result_text:
            raise HTTPException(
                status_code=502,
                detail="Model returned empty response",
            )
        # 将本次扫描保存到数据库（图片 + 文本，语音后续可选）
        if user_db and not _is_admin_role(user_role):
            # 成功拿到识别结果后再扣减/二次校验，避免 OpenAI 失败时错误扣额度
            consume_quota_after_success(user_db, db)

        record = sm.ScanRecord(
            user_id=user_id,
            artwork_code="unknown",
            image_path=image_path,
            text=result_text,
            audio_path=None,
        )
        db.session.add(record)
        db.session.commit()
        return {"text": result_text, "scan_id": str(record.scan_id)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Analyze failed: {exc}",
        ) from exc


async def _send_error(ws: WebSocket, message: str, code: str | None = None) -> None:
    try:
        payload: Dict[str, Any] = {"type": "error", "message": message}
        if code:
            payload["code"] = code
        await ws.send_json(payload)
    finally:
        await ws.close()


@app.get("/scan-quota/remaining", tags=[TAG.Analyze])
def get_scan_quota_remaining(
    user: sm.User = Depends(d.get_logged_in_user),
    db: MuseumDb = Depends(d.get_psql),
) -> Dict[str, Any]:
    """
    返回当前登录用户今日剩余可识别次数（UTC 口径）。
    """
    # 管理员不限制扫描次数：返回一个足够大的剩余值，避免前端展示“已用尽”。
    if _is_admin_role(getattr(user, "role", None)):
        return {
            "plan": "pro_monthly",
            "limit": 999999,
            "used": 0,
            "remaining": 999999,
        }

    now = dt.datetime.now(dt.timezone.utc)
    quota = get_quota_remaining(user, db.session, now=now)
    return {
        "plan": quota["plan"],
        "limit": quota["limit"],
        "used": quota["used"],
        "remaining": quota["remaining"],
        "pro_expires_at_ts": quota["pro_expires_at_ts"],
        "scan_pack_total": quota["scan_pack_total"],
        "daily_limit": FREE_DAILY_SCAN_LIMIT,
    }


async def _handle_analyze_websocket(ws: WebSocket) -> None:
    """
    WebSocket 流式分析：客户端发 type=start + image_base64 + mime_type，
    服务端回 type=delta（delta, full）和 type=done。
    """
    await ws.accept()
    gemini_flags = GeminiFlags.get()
    if not gemini_flags.api_key:
        await _send_error(ws, "GEMINI_API_KEY is not set")
        return

    try:
        init_msg: Dict[str, Any] = await ws.receive_json()
    except WebSocketDisconnect:
        return
    except Exception:
        await _send_error(ws, "Invalid init payload, expected JSON")
        return

    if init_msg.get("type") != "start":
        await _send_error(ws, "First message must be of type 'start'")
        return

    image_b64 = init_msg.get("image_base64")
    mime_type = (init_msg.get("mime_type") or "image/jpeg").strip()
    auth_token = init_msg.get("auth_token")

    if not image_b64 or not isinstance(image_b64, str):
        await _send_error(ws, "image_base64 is required")
        return
    if not mime_type.startswith("image/"):
        await _send_error(ws, "mime_type must start with 'image/'")
        return

    # 识别用户（优先使用 init 消息里的 token，其次使用 ws.scope.user）
    user_uuid: Optional[str] = None
    if auth_token and isinstance(auth_token, str):
        try:
            token = auth_token.strip()
            if token.lower().startswith("bearer "):
                token = token[len("bearer ") :].strip()
            payload = jwt.decode(
                token,
                flags.MuseumFlags.get().login_secret,
                algorithms=["HS256"],
            )
            raw_uuid = payload.get("user_id") or payload.get("user_uuid")
            if raw_uuid:
                user_uuid = str(raw_uuid)
        except Exception:
            user_uuid = None

    if not user_uuid:
        try:
            user_obj = ws.scope.get("user") if hasattr(ws, "scope") else None  # type: ignore[attr-defined]
            user_uuid = getattr(user_obj, "user_uuid", None)
            if user_uuid:
                user_uuid = str(user_uuid)
        except Exception:
            user_uuid = None

    # 已注册用户走订阅额度规则：Free / Scan Pack / Pro
    if auth_token and not user_uuid:
        # 客户端传了 auth_token 但解不出 user_id：不要静默写 NULL user_id
        await _send_error(
            ws, "Invalid or expired auth token", code="INVALID_AUTH_TOKEN"
        )
        return

    if user_uuid:
        with postgres_session() as db:
            user_role = (
                db.session.query(sm.User.role)
                .filter(sm.User.user_id == user_uuid)
                .scalar()
            )
            if not _is_admin_role(user_role):
                user_db = (
                    db.session.query(sm.User)
                    .filter(sm.User.user_id == user_uuid)
                    .one_or_none()
                )
                if not user_db:
                    await _send_error(
                        ws,
                        "Subscription not initialized.",
                        code="SUBSCRIPTION_NOT_READY",
                    )
                    return
                quota = get_quota_remaining(
                    user_db, db.session, now=dt.datetime.now(dt.timezone.utc)
                )
                if quota["remaining"] <= 0:
                    plan = quota["plan"]
                    if plan == "free":
                        code = "DAILY_SCAN_QUOTA_EXCEEDED"
                        msg = "Daily scan quota exceeded. Please try again tomorrow."
                    elif plan == "scan_pack":
                        code = "SCAN_PACK_QUOTA_EXCEEDED"
                        msg = "Scan pack quota exhausted."
                    elif plan in ("pro_monthly", "pro_yearly"):
                        code = "PRO_QUOTA_EXCEEDED"
                        msg = "Pro scan quota exhausted."
                    else:
                        code = "QUOTA_EXCEEDED"
                        msg = "Quota exhausted."
                    await _send_error(ws, msg, code=code)
                    return

    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        await _send_error(ws, "image_base64 is not valid base64")
        return

    # 保存图片到本地，供后续扫描记录使用
    image_path = _save_image_bytes(image_bytes, mime_type)

    image_url = f"data:{mime_type};base64,{image_b64}"
    client = AsyncOpenAI(api_key=gemini_flags.api_key, base_url=gemini_flags.base_url)
    model = gemini_flags.model
    full_text = ""

    raw_locale = init_msg.get("locale")
    lang_tag = raw_locale if isinstance(raw_locale, str) else None
    prompt_text = _analyze_prompt(_normalize_analyze_locale(lang_tag))

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            stream=True,
        )
    except Exception as exc:
        if model != GEMINI_FALLBACK_MODEL and _is_model_not_found_error(exc):
            stream = await client.chat.completions.create(
                model=GEMINI_FALLBACK_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                stream=True,
            )
        else:
            raise
    try:
        async for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0].delta, "content", None) or ""
            if not delta:
                continue
            full_text += delta
            await ws.send_json({"type": "delta", "delta": delta, "full": full_text})
            await asyncio.sleep(0)  # yield so WebSocket flushes immediately

        scan_id_str: Optional[str] = None

        # 将本次扫描保存到数据库（图片 + 文本）
        if full_text.strip():
            with postgres_session() as db:
                if user_uuid:
                    user_db = (
                        db.session.query(sm.User)
                        .filter(sm.User.user_id == user_uuid)
                        .one_or_none()
                    )
                    if user_db and not _is_admin_role(getattr(user_db, "role", None)):
                        try:
                            consume_quota_after_success(user_db, db)
                        except HTTPException as exc:
                            detail = exc.detail if isinstance(exc.detail, dict) else {}
                            code = (
                                detail.get("code") if isinstance(detail, dict) else None
                            )
                            msg = (
                                detail.get("message")
                                if isinstance(detail, dict)
                                else None
                            )
                            await _send_error(
                                ws, msg or "Scan quota exhausted.", code=code
                            )
                            return

                record = sm.ScanRecord(
                    user_id=user_uuid,
                    artwork_code="unknown",
                    image_path=image_path,
                    text=full_text,
                    audio_path=None,
                )
                db.session.add(record)
                db.session.commit()
                scan_id_str = str(record.scan_id)

        await ws.send_json({"type": "done", "scan_id": scan_id_str})
        await ws.close()
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await _send_error(ws, f"Analyze failed: {exc}")


__all__ = ["analyze_artwork", "_handle_analyze_websocket"]
