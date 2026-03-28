import json
import subprocess
from pathlib import Path
from .base import BaseVideoGenerator

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CLIPS_DIR = BASE_DIR / "media" / "clips"
VIDEO_DIR = BASE_DIR / "media" / "output"

DIMENSIONS = {
    "normal": (1280, 720),
    "tiktok": (720, 1280),
}


def _get_audio_duration(audio_path: str) -> float:
    """Return audio duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            audio_path,
        ],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "audio":
            return float(stream["duration"])
    raise RuntimeError(f"Could not determine audio duration for {audio_path}")


class FFmpegVideoGenerator(BaseVideoGenerator):
    """Video generation using local FFmpeg installation."""

    def generate(
        self,
        audio_path: str,
        image_path: str,
        output_filename: str,
        format: str = "normal",
    ) -> str:
        """Single image + audio → clip. Delegates to generate_slideshow."""
        return self.generate_slideshow(
            image_paths=[image_path],
            audio_path=audio_path,
            output_filename=output_filename,
            format=format,
        )

    def generate_slideshow(
        self,
        image_paths: list[str],
        audio_path: str,
        output_filename: str,
        format: str = "normal",
    ) -> str:
        """Multiple images shown sequentially over audio duration → single clip."""
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = CLIPS_DIR / output_filename
        width, height = DIMENSIONS.get(format, DIMENSIONS["normal"])

        audio_duration = _get_audio_duration(audio_path)
        num_images = len(image_paths)
        duration_per_image = audio_duration / num_images

        # Build filter_complex for slideshow:
        # Each image scaled to target size, shown for its slice of time,
        # all concatenated together with the audio overlaid.
        filter_parts = []
        inputs = []

        for i, img in enumerate(image_paths):
            inputs += ["-loop", "1", "-t", str(duration_per_image), "-i", img]
            filter_parts.append(
                f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24[v{i}];"
            )

        concat_inputs = "".join(f"[v{i}]" for i in range(num_images))
        filter_complex = (
            "".join(filter_parts)
            + f"{concat_inputs}concat=n={num_images}:v=1:a=0[vout]"
        )

        command = [
            "ffmpeg", "-y",
            *inputs,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", f"{num_images}:a",
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
            raise RuntimeError(f"FFmpeg slideshow failed: {result.stderr}")

        return str(output_path)

    def concat(self, clip_paths: list[str], output_filename: str) -> str:
        """Concatenate all segment clips into the final video."""
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
