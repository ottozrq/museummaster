import base64
import os
from typing import Iterable

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel

router = APIRouter()


class TTSRequest(BaseModel):
    text: str


def _ensure_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    return api_key


def _sanitize_text(text: str) -> str:
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    return text.strip()


def _stream_speech_bytes(text: str) -> Iterable[bytes]:
    api_key = _ensure_api_key()
    clean_text = _sanitize_text(text)

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    voice = os.getenv("OPENAI_TTS_VOICE", "alloy")

    try:
        # 使用 OpenAI 的流式 TTS 接口，边生成边返回字节
        with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=clean_text,
            response_format="mp3",
        ) as response:
            for chunk in response.iter_bytes():
                if chunk:
                    yield chunk
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - 保护性兜底
        raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc


@router.get("")
def text_to_speech_stream(text: str = Query(..., min_length=1)) -> StreamingResponse:
    """
    流式 TTS 接口：
    - 路径仍为 /tts，只是使用 GET /tts?text=xxx
    - 返回值是 audio/mpeg 的 HTTP streaming，前端可以直接用 URL 播放
    """
    return StreamingResponse(_stream_speech_bytes(text), media_type="audio/mpeg")


@router.post("")
def text_to_speech(payload: TTSRequest) -> dict:
    """
    兼容旧行为的 JSON 接口：
    - 仍然返回 base64 编码的 MP3，用于“收藏到本地文件”等需要完整音频的场景。
    """
    api_key = _ensure_api_key()
    clean_text = _sanitize_text(payload.text)

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    voice = os.getenv("OPENAI_TTS_VOICE", "alloy")

    try:
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=clean_text,
            response_format="mp3",
        )
        audio_bytes = response.read()
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        return {
            "audio_base64": audio_base64,
            "mime_type": "audio/mpeg",
            "voice": voice,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc
