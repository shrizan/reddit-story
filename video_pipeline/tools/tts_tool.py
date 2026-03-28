from pydantic import BaseModel
from crewai.tools import BaseTool
from video_pipeline.generators import get_tts_generator


class TTSInput(BaseModel):
    text: str
    filename: str = "audio.mp3"
    lang: str = "en"
    tld: str = "com"
    slow: bool = False


class TTSTool(BaseTool):
    name: str = "Text to Speech Tool"
    description: str = "Converts text to speech and saves it as an MP3 file."
    args_schema: type[BaseModel] = TTSInput

    def _run(
        self,
        text: str,
        filename: str = "audio.mp3",
        lang: str = "en",
        tld: str = "com",
        slow: bool = False,
    ) -> str:
        generator = get_tts_generator()
        return generator.generate(text=text, filename=filename, lang=lang, tld=tld, slow=slow)
