"""Artwork analysis: HTTP upload and WebSocket streaming."""

import asyncio
import base64
from typing import Any, Dict

from fastapi import File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI, OpenAI

from src.routes import TAG, app
from utils.flags import OpenAIFlags

PROMPT = (
    "你是一位专业的博物馆讲解员。请分析这张艺术品图片，并用中文输出详细讲解。"
    "内容必须包含并清晰分段："
    "1) 作品标题，2) 艺术家，3) 创作年份，4) 艺术风格，"
    "5) 历史背景，6) 艺术意义。如果信息不确定，请明确说明‘可能’并给出依据。"
)


@app.post("/analyze", tags=[TAG.Analyze])
async def analyze_artwork(image: UploadFile = File(...)) -> Dict[str, str]:
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
        return {"text": result_text}
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
        await ws.send_json({"type": "done"})
        await ws.close()
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await _send_error(ws, f"Analyze failed: {exc}")


__all__ = ["analyze_artwork", "_handle_analyze_websocket"]
