import asyncio
import subprocess
from pathlib import Path
from .base import BaseTTSGenerator

BASE_DIR = Path(__file__).resolve().parent.parent.parent
AUDIO_DIR = BASE_DIR / "media" / "audio"

# Maps (lang, tld, gender) → edge-tts voice name.
# tld follows the same convention as gTTS accents.
VOICE_MAP: dict[tuple[str, str, str], str] = {
    # English
    ("en", "com",    "female"): "en-US-JennyNeural",
    ("en", "com",    "male"):   "en-US-GuyNeural",
    ("en", "co.uk",  "female"): "en-GB-SoniaNeural",
    ("en", "co.uk",  "male"):   "en-GB-RyanNeural",
    ("en", "com.au", "female"): "en-AU-NatashaNeural",
    ("en", "com.au", "male"):   "en-AU-WilliamNeural",
    ("en", "ca",     "female"): "en-CA-ClaraNeural",
    ("en", "ca",     "male"):   "en-CA-LiamNeural",
    ("en", "co.in",  "female"): "en-IN-NeerjaNeural",
    ("en", "co.in",  "male"):   "en-IN-PrabhatNeural",
    ("en", "ie",     "female"): "en-IE-EmilyNeural",
    ("en", "ie",     "male"):   "en-IE-ConnorNeural",
    ("en", "co.za",  "female"): "en-ZA-LeahNeural",
    ("en", "co.za",  "male"):   "en-ZA-LukeNeural",
    ("en", "com.ng", "female"): "en-NG-EzinneNeural",
    ("en", "com.ng", "male"):   "en-NG-AbeoNeural",
    # Spanish
    ("es", "com", "female"): "es-ES-ElviraNeural",
    ("es", "com", "male"):   "es-ES-AlvaroNeural",
    # French
    ("fr", "com", "female"): "fr-FR-DeniseNeural",
    ("fr", "com", "male"):   "fr-FR-HenriNeural",
    # German
    ("de", "com", "female"): "de-DE-KatjaNeural",
    ("de", "com", "male"):   "de-DE-ConradNeural",
    # Italian
    ("it", "com", "female"): "it-IT-ElsaNeural",
    ("it", "com", "male"):   "it-IT-DiegoNeural",
    # Portuguese
    ("pt", "com", "female"): "pt-BR-FranciscaNeural",
    ("pt", "com", "male"):   "pt-BR-AntonioNeural",
    # Hindi
    ("hi", "com", "female"): "hi-IN-SwaraNeural",
    ("hi", "com", "male"):   "hi-IN-MadhurNeural",
    # Japanese
    ("ja", "com", "female"): "ja-JP-NanamiNeural",
    ("ja", "com", "male"):   "ja-JP-KeitaNeural",
}

_FALLBACK_FEMALE = "en-US-JennyNeural"
_FALLBACK_MALE   = "en-US-GuyNeural"


def _resolve_voice(lang: str, tld: str, gender: str) -> str:
    key = (lang, tld, gender)
    if key in VOICE_MAP:
        return VOICE_MAP[key]
    # Try lang + com fallback
    fallback_key = (lang, "com", gender)
    if fallback_key in VOICE_MAP:
        return VOICE_MAP[fallback_key]
    return _FALLBACK_MALE if gender == "male" else _FALLBACK_FEMALE


async def _synthesize(voice: str, text: str, path: str) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)


class EdgeTTSGenerator(BaseTTSGenerator):
    """TTS using Microsoft Edge TTS (free, no API key). Supports male/female voices.
    Speed is applied via FFmpeg atempo post-processing."""

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
        voice = _resolve_voice(lang, tld, gender)

        speed_val = float(speed)
        if abs(speed_val - 1.0) < 0.01:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_synthesize(voice, text, str(output_path)))
            finally:
                loop.close()
        else:
            tmp_path = AUDIO_DIR / f"_tmp_{filename}"
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_synthesize(voice, text, str(tmp_path)))
            finally:
                loop.close()
            self._apply_speed(tmp_path, output_path, speed_val)
            tmp_path.unlink(missing_ok=True)

        return str(output_path)

    def _apply_speed(self, src: Path, dst: Path, speed: float) -> None:
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
