from crewai import Agent, LLM
from video_pipeline.tools.tts_tool import TTSTool
from video_pipeline.tools.image_tool import ImageTool
from video_pipeline.tools.video_tool import VideoTool

# Lightweight LLM for agent reasoning — uses Gemini free tier
import os
gemini_llm = LLM(
    model="gemini/gemini-2.0-flash",
    api_key=os.environ.get("GEMINI_API_KEY"),
)


def tts_agent() -> Agent:
    return Agent(
        role="Text-to-Speech Converter",
        goal="Convert the story text into a clear, natural-sounding MP3 audio file.",
        backstory=(
            "You are an audio production specialist. Your job is to take story text "
            "and produce a high-quality narration audio file using the given voice settings."
        ),
        tools=[TTSTool()],
        llm=gemini_llm,
        verbose=True,
    )


def image_agent() -> Agent:
    return Agent(
        role="Cartoon Illustrator",
        goal="Generate a vibrant cartoon-style illustration that represents the story visually.",
        backstory=(
            "You are a digital artist specializing in cartoon illustrations. "
            "You create bright, engaging, child-friendly images that bring stories to life."
        ),
        tools=[ImageTool()],
        llm=gemini_llm,
        verbose=True,
    )


def video_agent() -> Agent:
    return Agent(
        role="Video Producer",
        goal="Combine the audio narration and illustration into a final MP4 video.",
        backstory=(
            "You are a video editor who merges audio and image files into polished video content "
            "using FFmpeg. You ensure the video plays smoothly with synchronized audio."
        ),
        tools=[VideoTool()],
        llm=gemini_llm,
        verbose=True,
    )
