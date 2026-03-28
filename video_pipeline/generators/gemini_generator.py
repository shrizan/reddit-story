import io
import os
from pathlib import Path
from PIL import Image
from google import genai
from google.genai import types
from .base import BaseImageGenerator

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGE_DIR = BASE_DIR / "media" / "images"

STYLE_PROMPTS = {
    "cartoon": "cartoon style illustration, bright colors, simple flat design, no text, child-friendly",
    "realistic": "photorealistic, highly detailed, cinematic lighting, no text",
    "watercolor": "watercolor painting, soft brush strokes, painterly, pastel tones, no text",
    "comic": "comic book style, bold black outlines, halftone shading, vivid colors, no text",
    "anime": "anime style illustration, Japanese animation, clean lines, expressive, no text",
    "ghibli": "Studio Ghibli style, Hayao Miyazaki inspired, hand-painted backgrounds, lush nature, warm soft lighting, whimsical atmosphere, no text",
    "pixel": "pixel art, retro 8-bit style, low resolution aesthetic, vibrant palette, no text",
    "sketch": "pencil sketch, hand-drawn, black and white, fine line detail, no text",
}


class GeminiImageGenerator(BaseImageGenerator):
    """Image generation using Gemini (gemini-2.5-flash-image)."""

    MODEL = "gemini-2.5-flash-image"

    ASPECT_RATIOS = {
        "normal": "16:9",
        "tiktok": "9:16",
    }

    def generate(self, text: str, filename: str, image_style: str = "cartoon", format: str = "normal") -> str:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        output_path = IMAGE_DIR / filename

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")

        client = genai.Client(api_key=api_key)

        style_description = STYLE_PROMPTS.get(image_style, STYLE_PROMPTS["cartoon"])
        orientation = "vertical portrait" if format == "tiktok" else "horizontal landscape"
        prompt = f"{style_description}, {orientation}: {text}"

        response = client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        candidates = response.candidates
        if not candidates:
            raise RuntimeError("Gemini returned no candidates — likely blocked by safety filters")

        candidate = candidates[0]
        if candidate.content is None:
            finish_reason = getattr(candidate, "finish_reason", "unknown")
            raise RuntimeError(f"Gemini candidate content is empty (finish_reason={finish_reason}). Try rephrasing the prompt.")

        for part in candidate.content.parts:
            if part.inline_data is not None:
                img = Image.open(io.BytesIO(part.inline_data.data))
                img.save(str(output_path))
                return str(output_path)

        raise RuntimeError("Gemini returned a response but no image data was found in the parts")
