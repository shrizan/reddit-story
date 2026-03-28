import logging
import os
from pathlib import Path
from .base import BaseImageGenerator

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGE_DIR = BASE_DIR / "media" / "images"

# Model IDs on HuggingFace
MODEL_IDS = {
    "flux-schnell": "black-forest-labs/FLUX.1-schnell",
    "flux-dev":     "black-forest-labs/FLUX.1-dev",
    "sdxl":         "stabilityai/stable-diffusion-xl-base-1.0",
}

STYLE_PROMPTS = {
    "cartoon":   "cartoon style illustration, bright colors, simple flat design, no text",
    "realistic": "photorealistic, highly detailed, cinematic lighting, no text",
    "watercolor":"watercolor painting, soft brush strokes, painterly, pastel tones, no text",
    "comic":     "comic book style, bold black outlines, halftone shading, vivid colors, no text",
    "anime":     "anime style illustration, Japanese animation, clean lines, expressive, no text",
    "ghibli":    "Studio Ghibli style, Hayao Miyazaki inspired, hand-painted backgrounds, lush nature, warm soft lighting, whimsical dreamy atmosphere, no text",
    "pixel":     "pixel art, retro 8-bit style, low resolution aesthetic, vibrant palette, no text",
    "sketch":    "pencil sketch, hand-drawn, black and white, fine line detail, no text",
}

# Cache loaded pipelines so the model is only loaded once per process
_pipeline_cache: dict[str, object] = {}


def _get_pipeline(model_key: str):
    """Load and cache the diffusion pipeline. Uses MPS on Apple Silicon."""
    if model_key in _pipeline_cache:
        return _pipeline_cache[model_key]

    import torch
    from diffusers import FluxPipeline, DiffusionPipeline

    model_id = MODEL_IDS.get(model_key, MODEL_IDS["flux-schnell"])

    # Determine best available device
    if torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.bfloat16
    elif torch.cuda.is_available():
        device = "cuda"
        dtype = torch.float16
    else:
        device = "cpu"
        dtype = torch.float32

    logger.info("Loading diffusion model %s on %s ...", model_id, device)

    if model_key in ("flux-schnell", "flux-dev"):
        pipe = FluxPipeline.from_pretrained(model_id, torch_dtype=dtype)
    else:
        pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=dtype)

    pipe = pipe.to(device)
    pipe.enable_attention_slicing()

    logger.info("Diffusion model loaded on %s", device)
    _pipeline_cache[model_key] = pipe
    return pipe


class DiffusionImageGenerator(BaseImageGenerator):
    """Local image generation using FLUX.1 or Stable Diffusion via HuggingFace diffusers."""

    def generate(
        self,
        text: str,
        filename: str,
        image_style: str = "ghibli",
        format: str = "normal",
        diffusion_model: str = "flux-schnell",
    ) -> str:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        output_path = IMAGE_DIR / filename

        model_key = os.environ.get("DIFFUSION_MODEL", diffusion_model)
        pipe = _get_pipeline(model_key)

        style_desc = STYLE_PROMPTS.get(image_style, STYLE_PROMPTS["ghibli"])
        orientation = "vertical portrait composition" if format == "tiktok" else "horizontal landscape composition"
        prompt = f"{style_desc}, {orientation}: {text}"

        width, height = (720, 1280) if format == "tiktok" else (1280, 720)

        logger.info("Generating image locally: model=%s style=%s", model_key, image_style)

        result = pipe(
            prompt=prompt,
            width=width,
            height=height,
            num_inference_steps=4 if "schnell" in model_key else 20,
            guidance_scale=0.0 if "schnell" in model_key else 3.5,
        )

        image = result.images[0]
        image.save(str(output_path))
        logger.info("Image saved to %s", output_path)

        return str(output_path)
