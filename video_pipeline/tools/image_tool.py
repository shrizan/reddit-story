from pydantic import BaseModel
from crewai.tools import BaseTool
from video_pipeline.generators import get_image_generator


class ImageInput(BaseModel):
    text: str
    filename: str = "image.png"
    image_style: str = "cartoon"
    format: str = "normal"


class ImageTool(BaseTool):
    name: str = "Image Generation Tool"
    description: str = "Generates a styled image from text and saves it as a PNG."
    args_schema: type[BaseModel] = ImageInput

    def _run(self, text: str, filename: str = "image.png", image_style: str = "cartoon", format: str = "normal") -> str:
        generator = get_image_generator()
        return generator.generate(text=text, filename=filename, image_style=image_style, format=format)
