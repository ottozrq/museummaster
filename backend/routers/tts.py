import base64
import os
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel

router = APIRouter()


class TTSRequest(BaseModel):
    text: str


@router.post("")
def text_to_speech(payload: TTSRequest) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    voice = os.getenv("OPENAI_TTS_VOICE", "alloy")

    try:
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=payload.text,
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
