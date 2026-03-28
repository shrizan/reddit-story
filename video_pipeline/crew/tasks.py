from crewai import Task
from crewai.agents.agent_builder.base_agent import BaseAgent


def tts_task(agent: BaseAgent, story_text: str, job_id: int, lang: str, accent: str, slow: bool) -> Task:
    return Task(
        description=(
            f"Convert the following story text to speech and save it as an MP3 file.\n\n"
            f"Story: {story_text}\n\n"
            f"Use these settings:\n"
            f"- filename: audio_{job_id}.mp3\n"
            f"- lang: {lang}\n"
            f"- tld: {accent}\n"
            f"- slow: {slow}\n\n"
            f"Call the Text to Speech Tool with these exact parameters and return the full file path."
        ),
        expected_output="The absolute file path to the saved MP3 audio file.",
        agent=agent,
    )


def image_task(agent: BaseAgent, story_text: str, job_id: int, image_style: str = "cartoon") -> Task:
    return Task(
        description=(
            f"Generate a {image_style}-style illustration for the following story and save it as a PNG.\n\n"
            f"Story: {story_text}\n\n"
            f"Use these settings:\n"
            f"- filename: image_{job_id}.png\n"
            f"- image_style: {image_style}\n\n"
            f"Call the Image Generation Tool with these exact parameters and return the full file path."
        ),
        expected_output="The absolute file path to the saved PNG image file.",
        agent=agent,
    )


def video_task(agent: BaseAgent, job_id: int, context: list) -> Task:
    return Task(
        description=(
            f"Merge the audio and image files produced by the previous tasks into a single MP4 video.\n\n"
            f"Use these settings:\n"
            f"- output_filename: video_{job_id}.mp4\n\n"
            f"Read the file paths from the previous task outputs, then call the Video Generation Tool "
            f"with audio_path, image_path, and output_filename. Return the full path to the video file."
        ),
        expected_output="The absolute file path to the saved MP4 video file.",
        agent=agent,
        context=context,
    )
