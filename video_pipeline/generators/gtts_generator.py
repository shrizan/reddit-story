import subprocess
from pathlib import Path
from gtts import gTTS
from .base import BaseTTSGenerator

BASE_DIR = Path(__file__).resolve().parent.parent.parent
AUDIO_DIR = BASE_DIR / "media" / "audio"


class GTTSGenerator(BaseTTSGenerator):
    """TTS using gTTS (free). Speed is applied via FFmpeg atempo post-processing.
    Voice gender is not supported by gTTS — the same voice is used regardless."""

    def generate(
        self,
        text: str,
        filename: str,
        lang: str = "en",
        tld: str = "com",
        speed: str = "1.0",
        gender: str = "female",
    ) -> str:
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        output_path = AUDIO_DIR / filename

        tts = gTTS(text=text, lang=lang, tld=tld, slow=False)

        speed_val = float(speed)
        if abs(speed_val - 1.0) < 0.01:
            # No speed change needed — save directly
            tts.save(str(output_path))
        else:
            # Save to a temp file, apply FFmpeg atempo, write to final path
            tmp_path = AUDIO_DIR / f"_tmp_{filename}"
            tts.save(str(tmp_path))
            self._apply_speed(tmp_path, output_path, speed_val)
            tmp_path.unlink(missing_ok=True)

        return str(output_path)

    def _apply_speed(self, src: Path, dst: Path, speed: float) -> None:
        """Apply speed multiplier to audio using FFmpeg atempo filter."""
        # atempo accepts 0.5–2.0; chain two filters for values outside that range
        if speed < 0.5:
            atempo = f"atempo={speed / 0.5},atempo=0.5"
        elif speed > 2.0:
            atempo = f"atempo=2.0,atempo={speed / 2.0}"
        else:
            atempo = f"atempo={speed}"

        command = [
            "ffmpeg", "-y",
            "-i", str(src),
            "-filter:a", atempo,
            str(dst),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg atempo failed: {result.stderr}")
