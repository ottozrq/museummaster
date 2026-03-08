"""Text-to-speech: streaming and JSON (base64) endpoints."""

import base64
from typing import Iterable

from fastapi import HTTPException, Query
from fastapi.responses import StreamingResponse
from openai import OpenAI

from src.routes import TAG, app
import models as m
from utils.flags import OpenAIFlags


def _openai_flags() -> OpenAIFlags:
    flags = OpenAIFlags.get()
    if not flags.api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    return flags


def _sanitize_text(text: str) -> str:
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    return text.strip()


def _stream_speech_bytes(text: str) -> Iterable[bytes]:
    flags = _openai_flags()
    clean_text = _sanitize_text(text)
    client = OpenAI(api_key=flags.api_key)
    model = flags.tts_model
    voice = flags.tts_voice
    try:
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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc


@app.get("/tts", tags=[TAG.TTS])
def text_to_speech_stream(
    text: str = Query(..., min_length=1),
) -> StreamingResponse:
    """流式 TTS：GET /tts?text=xxx，返回 audio/mpeg 流。"""
    return StreamingResponse(
        _stream_speech_bytes(text),
        media_type="audio/mpeg",
    )


@app.post("/tts", tags=[TAG.TTS])
def text_to_speech(payload: m.TTSRequest) -> dict:
    """POST /tts：JSON body {"text": "..."}，返回 base64 MP3。"""
    flags = _openai_flags()
    clean_text = _sanitize_text(payload.text)
    client = OpenAI(api_key=flags.api_key)
    model = flags.tts_model
    voice = flags.tts_voice
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
