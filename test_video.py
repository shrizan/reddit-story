"""
Phase 7 test — creates a dummy image then merges it with existing audio into a video.
"""
import environ
from pathlib import Path

env = environ.Env()
environ.Env.read_env(Path(__file__).resolve().parent / ".env")

from PIL import Image, ImageDraw, ImageFont

# --- create a simple test image ---
img = Image.new("RGB", (1280, 720), color=(70, 130, 180))
draw = ImageDraw.Draw(img)
draw.rectangle([40, 40, 1240, 680], outline="white", width=6)
draw.text((200, 300), "A fox lived in a forest and was very clever.", fill="white")

image_path = Path("media/images/test_image.png")
image_path.parent.mkdir(parents=True, exist_ok=True)
img.save(str(image_path))
print(f"Test image created: {image_path}")

# --- run video generator ---
from video_pipeline.generators.ffmpeg_generator import FFmpegVideoGenerator

gen = FFmpegVideoGenerator()
video_path = gen.generate(
    audio_path=str(Path("media/audio/test_audio.mp3").resolve()),
    image_path=str(image_path.resolve()),
    output_filename="test_video.mp4",
)
print(f"Video saved to: {video_path}")
