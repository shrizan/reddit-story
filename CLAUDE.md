# Reddit Video Project

## Stack
- Python 3.10, Django 4.2, CrewAI, uv for package management

## Run commands
- `uv run manage.py runserver`
- `uv run manage.py migrate`
- `uv sync` to install deps

## Agents
1. TTSAgent — gTTS, saves to media/audio.mp3
2. ImageAgent — Google Imagen via Vertex AI, saves to media/images/
3. VideoAgent — FFmpeg subprocess, saves to media/output.mp4

## Environment
- Copy .env.example to .env and fill in GCP_PROJECT_ID
- FFmpeg must be installed locally (brew install ffmpeg / apt install ffmpeg)

## Conventions
- Tools live in video_pipeline/tools/
- Each tool extends crewai.tools.BaseTool
- Use Pydantic BaseModel for tool inputs
