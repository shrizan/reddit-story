import environ
from pathlib import Path

env = environ.Env()
environ.Env.read_env(Path(__file__).resolve().parent / ".env")

from video_pipeline.tools.image_tool import ImageTool

tool = ImageTool()
result = tool._run(
    text="A clever fox sitting under a big tree in a forest",
    filename="test_image.png"
)
print(f"Image saved to: {result}")
