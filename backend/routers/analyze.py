import os
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from openai import OpenAI

router = APIRouter()

PROMPT = (
    "你是一位专业的博物馆讲解员。请分析这张艺术品图片，并用中文输出详细讲解。"
    "内容必须包含并清晰分段："
    "1) 作品标题，2) 艺术家，3) 创作年份，4) 艺术风格，5) 历史背景，6) 艺术意义。"
    "如果信息不确定，请明确说明‘可能’并给出依据。"
)


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

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
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

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")

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


__all__ = ["router", "_handle_analyze_websocket"]
