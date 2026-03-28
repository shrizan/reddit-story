import json
from django.db import models


class TTSSettings(models.Model):
    """Single-row table storing default TTS settings used in the Generate Story page."""

    LANG_CHOICES = [
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("de", "German"),
        ("it", "Italian"),
        ("pt", "Portuguese"),
        ("hi", "Hindi"),
        ("ja", "Japanese"),
    ]

    ACCENT_CHOICES = [
        ("com", "US English"),
        ("co.uk", "British English"),
        ("com.au", "Australian English"),
        ("ca", "Canadian English"),
        ("co.in", "Indian English"),
        ("ie", "Irish English"),
        ("co.za", "South African English"),
        ("com.ng", "Nigerian English"),
    ]

    SPEED_CHOICES = [
        ("0.5", "0.5× Very Slow"),
        ("0.75", "0.75× Slow"),
        ("1.0", "1.0× Normal"),
        ("1.25", "1.25× Fast"),
        ("1.5", "1.5× Faster"),
        ("2.0", "2.0× Very Fast"),
    ]

    VOICE_GENDER_CHOICES = [
        ("female", "Female"),
        ("male", "Male"),
    ]

    IMAGE_STYLE_CHOICES = [
        ("cartoon", "Cartoon"),
        ("realistic", "Realistic"),
        ("watercolor", "Watercolor"),
        ("comic", "Comic Book"),
        ("anime", "Anime"),
        ("ghibli", "Studio Ghibli"),
        ("pixel", "Pixel Art"),
        ("sketch", "Sketch"),
    ]

    FORMAT_CHOICES = [
        ("normal", "Normal (16:9 Landscape)"),
        ("tiktok", "TikTok (9:16 Vertical)"),
    ]

    DIFFUSION_MODEL_CHOICES = [
        ("flux-schnell", "FLUX.1 Schnell (Fast, great quality)"),
        ("flux-dev", "FLUX.1 Dev (Slower, best quality)"),
        ("sdxl", "Stable Diffusion XL"),
    ]

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, default="en")
    accent = models.CharField(max_length=20, choices=ACCENT_CHOICES, default="com")
    speed = models.CharField(max_length=10, choices=SPEED_CHOICES, default="1.0")
    voice_gender = models.CharField(max_length=10, choices=VOICE_GENDER_CHOICES, default="female")
    image_style = models.CharField(max_length=20, choices=IMAGE_STYLE_CHOICES, default="cartoon")
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default="normal")
    diffusion_model = models.CharField(max_length=20, choices=DIFFUSION_MODEL_CHOICES, default="flux-schnell")

    class Meta:
        verbose_name = "TTS Settings"
        verbose_name_plural = "TTS Settings"

    def __str__(self):
        return f"TTS Settings (lang={self.lang}, accent={self.accent}, speed={self.speed}, style={self.image_style})"

    @classmethod
    def get_defaults(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class StoryJob(models.Model):
    """Tracks the full pipeline lifecycle for each submitted story."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("rewriting_story", "Rewriting Story"),
        ("story_rewritten", "Story Rewritten"),
        ("splitting_story", "Splitting Story"),
        ("processing_segments", "Processing Segments"),
        ("merging_video", "Merging Video"),
        ("done", "Done"),
        ("stopped", "Stopped"),
        ("failed", "Failed"),
    ]

    LANG_CHOICES = TTSSettings.LANG_CHOICES
    ACCENT_CHOICES = TTSSettings.ACCENT_CHOICES
    SPEED_CHOICES = TTSSettings.SPEED_CHOICES
    VOICE_GENDER_CHOICES = TTSSettings.VOICE_GENDER_CHOICES
    IMAGE_STYLE_CHOICES = TTSSettings.IMAGE_STYLE_CHOICES
    FORMAT_CHOICES = TTSSettings.FORMAT_CHOICES
    DIFFUSION_MODEL_CHOICES = TTSSettings.DIFFUSION_MODEL_CHOICES

    # Input
    story_text = models.TextField()
    rewritten_text = models.TextField(blank=True, default="")

    # TTS options
    lang = models.CharField(max_length=10, choices=LANG_CHOICES, default="en")
    accent = models.CharField(max_length=20, choices=ACCENT_CHOICES, default="com")
    speed = models.CharField(max_length=10, choices=SPEED_CHOICES, default="1.0")
    voice_gender = models.CharField(max_length=10, choices=VOICE_GENDER_CHOICES, default="female")
    image_style = models.CharField(max_length=20, choices=IMAGE_STYLE_CHOICES, default="cartoon")
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default="normal")
    diffusion_model = models.CharField(max_length=20, choices=DIFFUSION_MODEL_CHOICES, default="flux-schnell")

    # Segment progress
    total_segments = models.IntegerField(default=0)
    completed_segments = models.IntegerField(default=0)

    # Pipeline status
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, default="")

    # Final output
    video_path = models.CharField(max_length=500, blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Story Job"
        verbose_name_plural = "Story Jobs"

    def __str__(self):
        preview = self.story_text[:60] + "..." if len(self.story_text) > 60 else self.story_text
        return f"[{self.status.upper()}] {preview}"

    @property
    def is_downloadable(self):
        return self.status == "done" and bool(self.video_path)

    @property
    def progress_display(self):
        if self.status == "processing_segments" and self.total_segments:
            return f"{self.completed_segments}/{self.total_segments}"
        return ""


class StorySegment(models.Model):
    """One segment of a story — has its own audio, images and clip."""

    job = models.ForeignKey(StoryJob, on_delete=models.CASCADE, related_name="segments")
    order = models.IntegerField()
    text = models.TextField()

    audio_path = models.CharField(max_length=500, blank=True, default="")
    # JSON list of image paths e.g. ["/path/img_1_1.png", "/path/img_1_2.png"]
    image_paths = models.TextField(blank=True, default="[]")
    clip_path = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["order"]
        verbose_name = "Story Segment"
        verbose_name_plural = "Story Segments"

    def __str__(self):
        return f"Segment {self.order} — Job #{self.job_id}"

    def get_image_paths(self) -> list[str]:
        try:
            return json.loads(self.image_paths)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_image_paths(self, paths: list[str]) -> None:
        self.image_paths = json.dumps(paths)
