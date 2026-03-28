from crewai import Crew, Process
from .agents import tts_agent, image_agent, video_agent
from .tasks import tts_task, image_task, video_task


def run_pipeline(
    story_text: str,
    job_id: int,
    lang: str = "en",
    accent: str = "com",
    slow: bool = False,
    image_style: str = "cartoon",
) -> dict:
    """
    Run the full TTS → Image → Video pipeline.

    Returns a dict with keys: audio_path, image_path, video_path
    """
    # Build agents
    tts = tts_agent()
    img = image_agent()
    vid = video_agent()

    # Build tasks
    t_tts = tts_task(tts, story_text, job_id, lang, accent, slow)
    t_image = image_task(img, story_text, job_id, image_style)
    t_video = video_task(vid, job_id, context=[t_tts, t_image])

    # Assemble crew — sequential: TTS and Image run first, then Video
    crew = Crew(
        agents=[tts, img, vid],
        tasks=[t_tts, t_image, t_video],
        process=Process.sequential,
        verbose=True,
    )

    crew.kickoff()

    # Derive output paths from known naming convention
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent.parent

    return {
        "audio_path": str(base / "media" / "audio" / f"audio_{job_id}.mp3"),
        "image_path": str(base / "media" / "images" / f"image_{job_id}.png"),
        "video_path": str(base / "media" / "output" / f"video_{job_id}.mp4"),
    }
