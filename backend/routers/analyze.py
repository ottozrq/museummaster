import base64
from typing import Any, Dict

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from openai import OpenAI

from utils.flags import OpenAIFlags

router = APIRouter()

PROMPT = (
    "你是一位专业的博物馆讲解员。请分析这张艺术品图片，并用中文输出详细讲解。"
    "内容必须包含并清晰分段："
    "1) 作品标题，2) 艺术家，3) 创作年份，4) 艺术风格，5) 历史背景，6) 艺术意义。"
    "如果信息不确定，请明确说明‘可能’并给出依据。"
)


@router.post("")
async def analyze_artwork(image: UploadFile = File(...)) -> Dict[str, str]:
    """
    非流式 analyze 接口，供现有单元测试和同步调用使用。

    - 接收图片文件
    - 使用 OpenAI Responses API 生成完整讲解文本
    - 返回 {"text": "..."} JSON
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
        raise HTTPException(
            status_code=400,
            detail="Image is empty",
        )

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
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Analyze failed: {exc}",
        ) from exc


async def _send_error(ws: WebSocket, message: str) -> None:
    """Send a structured error message over WebSocket and close."""
    try:
        await ws.send_json({"type": "error", "message": message})
    finally:
        await ws.close()


async def _handle_analyze_websocket(ws: WebSocket) -> None:
    """
    WebSocket 版本的识别核心逻辑。

    - 客户端连接后发送一条 JSON：
      { "type": "start", "image_base64": "...", "mime_type": "image/jpeg" }
    - 服务端使用 Responses API 流式调用模型，
      并把增量结果通过 JSON 发送给前端：
      { "type": "delta", "delta": "...", "full": "到目前为止的完整文本" }
    - 结束时发送：
      { "type": "done" }
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

    client = OpenAI(api_key=openai_flags.api_key)
    model = openai_flags.museum_model

    full_text = ""

    try:
        # 使用 Responses API 的流式模式
        with client.responses.stream(
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
            for event in stream:
                event_type = getattr(event, "type", None)
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    if not delta:
                        continue
                    full_text += delta
                    await ws.send_json(
                        {"type": "delta", "delta": delta, "full": full_text}
                    )
                elif event_type == "response.completed":
                    break

        await ws.send_json({"type": "done"})
        await ws.close()
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover
        await _send_error(ws, f"Analyze failed: {exc}")


__all__ = ["router", "analyze_artwork", "_handle_analyze_websocket"]
