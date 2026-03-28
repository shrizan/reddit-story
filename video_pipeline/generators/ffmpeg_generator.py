import subprocess
from pathlib import Path
from .base import BaseVideoGenerator

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CLIPS_DIR = BASE_DIR / "media" / "clips"
VIDEO_DIR = BASE_DIR / "media" / "output"

DIMENSIONS = {
    "normal": "1280:720",
    "tiktok": "720:1280",
}


class FFmpegVideoGenerator(BaseVideoGenerator):
    """Video generation using local FFmpeg installation."""

    def generate(
        self,
        audio_path: str,
        image_path: str,
        output_filename: str,
        format: str = "normal",
    ) -> str:
        """Merge audio + image into a clip. Saved to media/clips/."""
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = CLIPS_DIR / output_filename
        scale = DIMENSIONS.get(format, DIMENSIONS["normal"])

        command = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-vf", f"scale={scale}",
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output_path),
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        return str(output_path)

    def concat(self, clip_paths: list[str], output_filename: str) -> str:
        """Concatenate all segment clips into the final video. Saved to media/output/."""
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        output_path = VIDEO_DIR / output_filename
        concat_file = VIDEO_DIR / f"_concat_{output_filename}.txt"

        with open(concat_file, "w") as f:
            for path in clip_paths:
                f.write(f"file '{path}'\n")

        command = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path),
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        concat_file.unlink(missing_ok=True)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")

        return str(output_path)
