"""Artwork analysis: HTTP upload and WebSocket streaming."""

import asyncio
import base64
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import (
    Depends,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from openai import AsyncOpenAI, OpenAI

import sql_models as sm
from src.routes import TAG, MuseumDb, app, d
from utils.flags import OpenAIFlags

IMAGE_DIR = Path("static") / "uploads" / "scans"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)


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


PROMPT = (
    "你是一位专业的博物馆讲解员。请分析这张艺术品图片，并用中文输出详细讲解。"
    "内容必须包含并清晰分段："
    "1) 作品标题，2) 艺术家，3) 创作年份，4) 艺术风格，"
    "5) 历史背景，6) 艺术意义。如果信息不确定，请明确说明‘可能’并给出依据。"
)


@app.post("/analyze", tags=[TAG.Analyze])
async def analyze_artwork(
    image: UploadFile = File(...),
    db: MuseumDb = Depends(d.get_psql),
    user: Optional[sm.User] = Depends(d.get_optional_logged_in_user),
) -> Dict[str, str]:
    """
    非流式 analyze：接收图片，用 OpenAI Responses API 生成讲解，返回 {"text": "..."}。
    """
    openai_flags = OpenAIFlags.get()
    if not openai_flags.api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    content_type = image.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image is empty")
    # 保存原始图片到本地文件系统
    image_path = _save_image_bytes(image_bytes, content_type)

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:{content_type};base64,{image_b64}"
    client = OpenAI(api_key=openai_flags.api_key)
    model = openai_flags.museum_model

    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT},
                        {"type": "input_image", "image_url": image_url},
                    ],
                }
            ],
        )
        result_text = response.output_text.strip()
        if not result_text:
            raise HTTPException(
                status_code=502,
                detail="Model returned empty response",
            )
        # 将本次扫描保存到数据库（图片 + 文本，语音后续可选）
        record = sm.ScanRecord(
            user_id=getattr(user, "user_id", None),
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


async def _send_error(ws: WebSocket, message: str) -> None:
    try:
        await ws.send_json({"type": "error", "message": message})
    finally:
        await ws.close()


async def _handle_analyze_websocket(ws: WebSocket) -> None:
    """
    WebSocket 流式分析：客户端发 type=start + image_base64 + mime_type，
    服务端回 type=delta（delta, full）和 type=done。
    """
    await ws.accept()
    openai_flags = OpenAIFlags.get()
    if not openai_flags.api_key:
        await _send_error(ws, "OPENAI_API_KEY is not set")
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
    if not image_b64 or not isinstance(image_b64, str):
        await _send_error(ws, "image_base64 is required")
        return
    if not mime_type.startswith("image/"):
        await _send_error(ws, "mime_type must start with 'image/'")
        return
    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        await _send_error(ws, "image_base64 is not valid base64")
        return

    # 保存图片到本地，供后续扫描记录使用
    image_path = _save_image_bytes(image_bytes, mime_type)

    image_url = f"data:{mime_type};base64,{image_b64}"
    client = AsyncOpenAI(api_key=openai_flags.api_key)
    model = openai_flags.museum_model
    full_text = ""

    try:
        async with client.responses.stream(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT},
                        {"type": "input_image", "image_url": image_url},
                    ],
                }
            ],
        ) as stream:
            async for event in stream:
                event_type = getattr(event, "type", None)
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    if not delta:
                        continue
                    full_text += delta
                    await ws.send_json(
                        {"type": "delta", "delta": delta, "full": full_text}
                    )
                    await asyncio.sleep(0)  # yield so WebSocket flushes immediately
                elif event_type == "response.completed":
                    break

        scan_id_str: Optional[str] = None

        # 将本次扫描保存到数据库（图片 + 文本）
        if full_text.strip():
            from utils.utils import postgres_session

            # 在某些部署环境里 WebSocket 可能没有挂载 AuthenticationMiddleware，
            # 此时访问 ws.user 会直接抛出 RuntimeError，这里统一视为匿名用户。
            user_obj = None
            try:
                if hasattr(ws, "scope"):
                    user_obj = ws.scope.get("user")  # type: ignore[assignment]
            except Exception:
                user_obj = None
            if not user_obj:
                try:
                    user_obj = getattr(ws, "user", None)
                except Exception:
                    user_obj = None

            user_uuid = getattr(user_obj, "user_uuid", None)
            with postgres_session() as db:
                record = sm.ScanRecord(
                    user_id=str(user_uuid) if user_uuid else None,
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
