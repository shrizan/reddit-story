from abc import ABC, abstractmethod


class BaseTTSGenerator(ABC):
    """Abstract interface for Text-to-Speech providers."""

    @abstractmethod
    def generate(
        self,
        text: str,
        filename: str,
        lang: str = "en",
        tld: str = "com",
        speed: str = "1.0",
        gender: str = "female",
    ) -> str:
        """Convert text to speech and save as MP3. Returns absolute file path."""
        ...


class BaseImageGenerator(ABC):
    """Abstract interface for Image Generation providers."""

    @abstractmethod
    def generate(self, text: str, filename: str, image_style: str = "cartoon", format: str = "normal") -> str:
        """Generate a styled image from text and save as PNG. Returns absolute file path."""
        ...


class BaseStoryRewriter(ABC):
    """Abstract interface for Story Rewriting/Summarization providers."""

    @abstractmethod
    def rewrite(self, text: str) -> str:
        """Clean and shorten raw story text. Returns the rewritten story."""
        ...


class BaseImagePromptGenerator(ABC):
    """Abstract interface for generating image prompts from story text."""

    @abstractmethod
    def generate_prompt(self, text: str, image_style: str = "cartoon") -> str:
        """Generate a detailed image generation prompt from a story segment."""
        ...


class BaseVideoGenerator(ABC):
    """Abstract interface for Video Generation providers."""

    @abstractmethod
    def generate(
        self,
        audio_path: str,
        image_path: str,
        output_filename: str,
        format: str = "normal",
    ) -> str:
        """Merge audio + image into a single clip. Saves to media/clips/. Returns absolute path."""
        ...

    @abstractmethod
    def concat(self, clip_paths: list[str], output_filename: str) -> str:
        """Concatenate multiple clips into one final video. Saves to media/output/. Returns absolute path."""
        ...
