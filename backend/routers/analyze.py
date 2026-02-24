import base64
import os
from fastapi import APIRouter, File, HTTPException, UploadFile
from openai import OpenAI

router = APIRouter()

PROMPT = (
    "你是一位专业的博物馆讲解员。请分析这张艺术品图片，并用中文输出详细讲解。"
    "内容必须包含并清晰分段："
    "1) 作品标题，2) 艺术家，3) 创作年份，4) 艺术风格，5) 历史背景，6) 艺术意义。"
    "如果信息不确定，请明确说明‘可能’并给出依据。"
)


@router.post("")
async def analyze_artwork(image: UploadFile = File(...)) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    content_type = image.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image is empty")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:{content_type};base64,{image_b64}"

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")

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
            raise HTTPException(status_code=502, detail="Model returned empty response")

        return {"text": result_text}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analyze failed: {exc}") from exc
