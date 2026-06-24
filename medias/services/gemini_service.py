import os
from pathlib import Path
from google import genai
from google.genai import types
from .gemini_eval import extract_json

from .gemini_eval import (
    PROMPT,
    resize_and_encode_image,
    call_gemini_with_retry,
)

def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")
    return genai.Client(api_key=api_key)

def analyze_ingredients(file_obj) -> dict:
    """
    파일 객체를 직접 받아서 Gemini로 분석
    file_obj: request.FILES에서 온 InMemoryUploadedFile
    """
    client = get_gemini_client()

    image_data = file_obj.read()
    mime_type = file_obj.content_type  # 'image/jpeg' 등

    image_part = types.Part.from_bytes(data=image_data, mime_type=mime_type)

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[PROMPT, image_part],
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            max_output_tokens=2048,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        ),
    )

    return extract_json(response.text or "")