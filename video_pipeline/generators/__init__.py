import os
from .base import (
    BaseTTSGenerator,
    BaseImageGenerator,
    BaseVideoGenerator,
    BaseStoryRewriter,
    BaseImagePromptGenerator,
)
from .gtts_generator import GTTSGenerator
from .edge_tts_generator import EdgeTTSGenerator
from .gemini_generator import GeminiImageGenerator
from .ffmpeg_generator import FFmpegVideoGenerator


def get_tts_generator() -> BaseTTSGenerator:
    provider = os.environ.get("TTS_PROVIDER", "gtts").lower()
    if provider == "gtts":
        return GTTSGenerator()
    if provider == "edge":
        return EdgeTTSGenerator()
    raise ValueError(f"Unknown TTS provider: '{provider}'. Valid options: gtts, edge")


def get_image_generator() -> BaseImageGenerator:
    provider = os.environ.get("IMAGE_PROVIDER", "gemini").lower()
    if provider == "gemini":
        return GeminiImageGenerator()
    raise ValueError(f"Unknown image provider: '{provider}'. Valid options: gemini")


def get_video_generator() -> BaseVideoGenerator:
    provider = os.environ.get("VIDEO_PROVIDER", "ffmpeg").lower()
    if provider == "ffmpeg":
        return FFmpegVideoGenerator()
    raise ValueError(f"Unknown video provider: '{provider}'. Valid options: ffmpeg")


def get_story_rewriter() -> BaseStoryRewriter:
    provider = os.environ.get("REWRITER_PROVIDER", "ollama").lower()
    if provider == "ollama":
        from .ollama_generator import OllamaRewriter
        return OllamaRewriter()
    if provider in ("falconsai", "distilbart"):
        from .falconsai_rewriter import FalconsaiRewriter
        return FalconsaiRewriter()
    raise ValueError(f"Unknown rewriter provider: '{provider}'. Valid options: ollama, distilbart")


def get_image_prompt_generator() -> BaseImagePromptGenerator:
    provider = os.environ.get("IMAGE_PROMPT_PROVIDER", "ollama").lower()
    if provider == "ollama":
        from .ollama_generator import OllamaImagePromptGenerator
        return OllamaImagePromptGenerator()
    raise ValueError(f"Unknown image prompt provider: '{provider}'. Valid options: ollama")


def use_text_summarization() -> bool:
    return os.environ.get("USE_TEXT_SUMMARIZATION", "false").lower() == "true"


def use_image_prompt_generation() -> bool:
    return os.environ.get("USE_IMAGE_PROMPT_GENERATION", "true").lower() == "true"
