"""Text-to-speech: streaming and JSON (base64) endpoints."""

import base64
from pathlib import Path
from typing import Iterable, Optional

from fastapi import Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openai import OpenAI

import models as m
import sql_models as sm
from src.routes import TAG, MuseumDb, app, d
from utils.flags import OpenAIFlags


def _openai_flags() -> OpenAIFlags:
    flags = OpenAIFlags.get()
    if not flags.api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set",
        )
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


AUDIO_DIR = Path("static") / "uploads" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _save_audio_bytes(audio_bytes: bytes) -> str:
    prefix = base64.urlsafe_b64encode(audio_bytes[:8]).decode("ascii").rstrip("=")
    filename = f"tts_{prefix}.mp3"
    target_path = AUDIO_DIR / filename
    target_path.write_bytes(audio_bytes)
    relative = target_path.relative_to("static")
    return f"/static/{relative.as_posix()}"


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
def text_to_speech(
    payload: m.TTSRequest,
    db: MuseumDb = Depends(d.get_psql),
) -> dict:
    """POST /tts：JSON body {"text": "..."}，返回 base64 MP3。"""
    clean_text = _sanitize_text(payload.text)
    flags = _openai_flags()
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
        audio_path = _save_audio_bytes(audio_bytes)

        # 可选：将音频路径写回对应的 ScanRecord
        if payload.scan_id is not None:
            record: Optional[sm.ScanRecord] = db.session.get(
                sm.ScanRecord, str(payload.scan_id)
            )
            if record:
                record.audio_path = audio_path
                db.session.add(record)
                db.session.commit()

        return {
            "audio_base64": audio_base64,
            "mime_type": "audio/mpeg",
            "voice": voice,
            "audio_path": audio_path,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc
