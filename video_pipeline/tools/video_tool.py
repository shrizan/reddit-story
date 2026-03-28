from pydantic import BaseModel
from crewai.tools import BaseTool
from video_pipeline.generators import get_video_generator


class VideoInput(BaseModel):
    audio_path: str
    image_path: str
    output_filename: str = "output.mp4"
    format: str = "normal"


class VideoTool(BaseTool):
    name: str = "Video Generation Tool"
    description: str = "Merges an audio file and an image into an MP4 video using FFmpeg."
    args_schema: type[BaseModel] = VideoInput

    def _run(self, audio_path: str, image_path: str, output_filename: str = "output.mp4", format: str = "normal") -> str:
        generator = get_video_generator()
        return generator.generate(
            audio_path=audio_path,
            image_path=image_path,
            output_filename=output_filename,
            format=format,
        )
