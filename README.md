# Reddit Story Video Generator

A Django-based pipeline that converts Reddit stories into narrated video content with AI-generated illustrations. Supports multiple TTS engines, image generators, and output formats (16:9 landscape or 9:16 TikTok vertical).

## Features

- **Story rewriting** — Optionally rewrites raw Reddit text into a polished narrative script via Ollama
- **Smart segmentation** — Splits stories into 25–80 word chunks at natural sentence/paragraph boundaries
- **Text-to-speech** — gTTS (Google) or Edge TTS (Microsoft) with 8 languages, 8 accents, and male/female voices
- **AI image generation** — Google Gemini or local FLUX/SDXL diffusion models with 8 visual styles
- **Video composition** — FFmpeg-based slideshow clips merged into a final MP4
- **Parallel processing** — Images generated concurrently with configurable workers and retry logic
- **Pipeline management** — Stop, resume, and regenerate jobs from the Django admin interface
- **Dual format** — 16:9 landscape and 9:16 vertical (TikTok) output

## Stack

- **Python 3.13+**, **Django 5.2**, **CrewAI**
- **uv** for package management
- **FFmpeg** for audio/video processing

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (`pip install uv`)
- FFmpeg (`brew install ffmpeg` on macOS, `apt install ffmpeg` on Linux)
- A [Google Gemini API key](https://aistudio.google.com/) (for image generation)
- [Ollama](https://ollama.com/) running locally (optional, for story rewriting and enhanced image prompts)

## Setup

**1. Clone and install dependencies**

```bash
git clone <repo-url>
cd reddit-story
uv sync
```

**2. Configure environment**

```bash
cp .env.example .env
```

Edit `.env` and set your values (see [Environment Variables](#environment-variables)).

**3. Run migrations**

```bash
uv run manage.py migrate
```

**4. Create a superuser**

```bash
uv run manage.py createsuperuser
```

**5. Start the development server**

```bash
uv run manage.py runserver
```

Open [http://localhost:8000/admin](http://localhost:8000/admin) and log in.

## Usage

1. Navigate to **Admin → Story Jobs → Generate Story**
2. Paste your Reddit story text
3. Choose your settings (language, accent, speed, image style, format)
4. Click **Generate** — the pipeline runs in the background
5. Monitor progress in the changelist (page auto-refreshes while processing)
6. Once status shows **done**, click **Download** to get the MP4

### Job Actions

| Action | Description |
|--------|-------------|
| **Download** | Download the final MP4 |
| **Stop** | Gracefully halt after the current segment |
| **Resume** | Restart from the last checkpoint (skips completed segments) |
| **Regenerate** | Full restart, clearing all intermediate files |

## Environment Variables

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Providers (swap to change backend)
TTS_PROVIDER=gtts                  # gtts | edge
IMAGE_PROVIDER=gemini              # gemini | diffusion
VIDEO_PROVIDER=ffmpeg              # ffmpeg (only option)

# Story rewriting via LLM (optional)
USE_TEXT_SUMMARIZATION=true
REWRITER_PROVIDER=ollama           # ollama | distilbart

# Image prompt enhancement via LLM (optional)
USE_IMAGE_PROMPT_GENERATION=true
IMAGE_PROMPT_PROVIDER=ollama

# Ollama config
OLLAMA_MODEL=kimi-k2.5:cloud
OLLAMA_BASE_URL=http://localhost:11434

# Generation tuning
IMAGES_PER_SEGMENT=2
IMAGE_GENERATION_WORKERS=3
IMAGE_GENERATION_RETRIES=3
```

## Project Structure

```
reddit-story/
├── config/                  # Django project settings and URL routing
├── video_pipeline/
│   ├── models.py            # TTSSettings, StoryJob, StorySegment
│   ├── pipeline.py          # Async pipeline orchestration (run/resume/stop)
│   ├── splitter.py          # Story segmentation (25–80 words per chunk)
│   ├── text_sanitizer.py    # Reddit markdown/emoji/URL stripping
│   ├── admin.py             # Custom Django admin views and actions
│   ├── crew/                # CrewAI agents and task definitions
│   │   ├── agents.py        # TTSAgent, ImageAgent, VideoAgent
│   │   ├── tasks.py         # Task definitions
│   │   └── crew.py          # Sequential crew orchestration
│   ├── generators/          # Pluggable provider implementations
│   │   ├── base.py          # Abstract base classes
│   │   ├── gtts_generator.py
│   │   ├── edge_tts_generator.py
│   │   ├── gemini_generator.py
│   │   ├── diffusion_generator.py
│   │   ├── ffmpeg_generator.py
│   │   ├── ollama_generator.py
│   │   └── falconsai_rewriter.py
│   └── tools/               # CrewAI BaseTool wrappers
│       ├── tts_tool.py
│       ├── image_tool.py
│       └── video_tool.py
├── media/                   # Generated output (gitignored)
│   ├── audio/               # Per-segment MP3 files
│   ├── images/              # Per-segment generated images
│   ├── clips/               # Per-segment video clips
│   └── output/              # Final merged MP4 videos
├── .env.example
├── pyproject.toml
└── manage.py
```

## Pipeline Flow

```
Submit story
    |
    v
[Optional] Rewrite via Ollama
    |
    v
Split into segments (25-80 words each)
    |
    v
For each segment:
  |- Generate audio  ---- TTS (gTTS / Edge TTS)
  |- Generate images ---- Parallel workers (Gemini / Diffusion)
  `- Create clip     ---- FFmpeg slideshow + audio
    |
    v
Merge all clips -> final MP4
    |
    v
Download via admin
```

**Job status progression:**
`pending` → `rewriting_story` → `story_rewritten` → `splitting_story` → `processing_segments` → `merging_video` → `done`

## Providers

### Text-to-Speech

| Provider | Key Required | Gender | Notes |
|----------|-------------|--------|-------|
| `gtts` | No | No | Google TTS, free |
| `edge` | No | Yes | Microsoft Edge TTS, free, wider voice selection |

### Image Generation

| Provider | Key Required | Notes |
|----------|-------------|-------|
| `gemini` | Yes (GEMINI_API_KEY) | Gemini 2.5 Flash Image |
| `diffusion` | No | Local FLUX.1 / SDXL; GPU recommended |

### Story Rewriting

| Provider | Notes |
|----------|-------|
| `ollama` | Requires Ollama running locally with a model pulled |
| `distilbart` | HuggingFace transformers, runs locally |

## Image Styles

`cartoon` · `realistic` · `watercolor` · `comic` · `anime` · `ghibli` · `pixel` · `sketch`

## Development

**Run standalone generator tests:**

```bash
uv run test_tts.py
uv run test_image.py
uv run test_video.py
```

**Run Django tests:**

```bash
uv run manage.py test
```

## Notes

- The admin interface is the primary UI — there are no public-facing views
- `media/` files are not tracked by git; back up the folder if you need to keep generated videos
- For production use, replace the hardcoded `SECRET_KEY` in `settings.py`, set `DEBUG=False`, and configure `ALLOWED_HOSTS`
- The diffusion image provider will automatically use Apple Silicon MPS, NVIDIA CUDA, or CPU fallback
