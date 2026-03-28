import os
import ollama
from .base import BaseStoryRewriter, BaseImagePromptGenerator


def _get_client() -> ollama.Client:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return ollama.Client(host=base_url)


def _get_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "kimi-k2.5:cloud")


class OllamaRewriter(BaseStoryRewriter):
    """
    Rewrites raw Reddit stories into clean, concise narration-ready text
    using a local Ollama model.
    """

    def rewrite(self, text: str) -> str:
        client = _get_client()
        model = _get_model()

        prompt = (
            "You are a professional scriptwriter for viral storytelling videos on TikTok and YouTube. "
            "Your job is to rewrite Reddit stories into gripping, emotionally engaging narration scripts.\n\n"
            "Rules:\n"
            "- Hook the listener in the very first sentence — start with the most dramatic or intriguing moment\n"
            "- Keep it concise: cut Reddit jargon, edit notes, usernames, and filler completely\n"
            "- Write in first person, past tense, as if telling a friend the story out loud\n"
            "- Use short punchy sentences for dramatic moments, longer ones for build-up\n"
            "- Add emotional tension — make the listener feel suspense, shock, empathy, or satisfaction\n"
            "- End with a strong closing line that feels satisfying or thought-provoking\n"
            "- No bullet points, no headers, no markdown, no meta-commentary\n"
            "- Plain paragraphs only, ready to be read aloud\n\n"
            f"Original story:\n{text}\n\n"
            "Rewritten script:"
        )

        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.message.content.strip()


class OllamaImagePromptGenerator(BaseImagePromptGenerator):
    """
    Generates detailed image generation prompts from story segments
    using a local Ollama model.
    """

    def generate_prompt(self, text: str, image_style: str = "cartoon") -> str:
        client = _get_client()
        model = _get_model()

        prompt = (
            f"You are an expert at writing image generation prompts. "
            f"Based on the following story segment, write a single detailed image generation prompt.\n\n"
            f"Requirements:\n"
            f"- Style: {image_style}\n"
            f"- Describe the scene visually (characters, setting, mood, colors)\n"
            f"- No text or words in the image\n"
            f"- One paragraph, no bullet points\n"
            f"- Focus on what should be SEEN, not what is said\n\n"
            f"Story segment:\n{text}\n\n"
            f"Image prompt:"
        )

        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.message.content.strip()
