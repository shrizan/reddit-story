import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import django
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

# Maps job_id → threading.Event; set the event to request a stop.
_stop_events: dict[int, threading.Event] = {}
_stop_events_lock = threading.Lock()


def request_stop(job_id: int) -> None:
    """Signal a running pipeline to stop after the current segment."""
    with _stop_events_lock:
        event = _stop_events.get(job_id)
        if event:
            event.set()


def _is_stop_requested(job_id: int) -> bool:
    with _stop_events_lock:
        event = _stop_events.get(job_id)
        return event is not None and event.is_set()


def _register_stop_event(job_id: int) -> threading.Event:
    event = threading.Event()
    with _stop_events_lock:
        _stop_events[job_id] = event
    return event


def _unregister_stop_event(job_id: int) -> None:
    with _stop_events_lock:
        _stop_events.pop(job_id, None)


def _set_status(job, status: str, extra_fields: list = None) -> None:
    job.status = status
    fields = ["status", "updated_at"] + (extra_fields or [])
    job.save(update_fields=fields)


def _ensure_django():
    if not django_settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        django.setup()


def _generate_single_image_with_retry(img_gen, image_text, job_id, seg_order, img_index, image_style, format):
    """Generate one image with retry. Returns the saved file path."""
    retries = int(os.environ.get("IMAGE_GENERATION_RETRIES", "3"))
    filename = f"image_{job_id}_{seg_order}_{img_index}.png"

    last_exc = None
    for attempt in range(retries):
        try:
            logger.info(
                "[Job %s] Seg %s img %s — requesting image (attempt %d/%d)...",
                job_id, seg_order, img_index, attempt + 1, retries,
            )
            path = img_gen.generate(
                text=image_text,
                filename=filename,
                image_style=image_style,
                format=format,
            )
            logger.info("[Job %s] Seg %s img %s — saved to %s", job_id, seg_order, img_index, path)
            return path
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "[Job %s] Seg %s img %s — attempt %d failed: %s",
                job_id, seg_order, img_index, attempt + 1, exc,
            )
            if attempt < retries - 1:
                wait = 2 ** attempt
                logger.info("[Job %s] Seg %s img %s — retrying in %ds...", job_id, seg_order, img_index, wait)
                time.sleep(wait)

    raise RuntimeError(
        f"Image generation failed for segment {seg_order} image {img_index} "
        f"after {retries} attempts: {last_exc}"
    )


def _generate_images_for_segment(img_gen, prompt_gen, seg, job_id, image_style, format, num_images):
    """Generate all images for one segment. Returns (seg.order, [path1, path2, ...])."""
    from video_pipeline.text_sanitizer import sanitize_for_tts

    base_text = sanitize_for_tts(seg.text)

    if prompt_gen is not None:
        logger.info("[Job %s] Seg %s — generating image prompt via LLM...", job_id, seg.order)
        image_text = prompt_gen.generate_prompt(text=base_text, image_style=image_style)
        logger.info("[Job %s] Seg %s — image prompt: %s", job_id, seg.order, image_text[:120])
    else:
        image_text = base_text

    paths = []
    for i in range(num_images):
        path = _generate_single_image_with_retry(
            img_gen, image_text, job_id, seg.order, i + 1, image_style, format
        )
        paths.append(path)

    return seg.order, paths


class PipelineStoppedError(Exception):
    pass


def _process_segments(job, segments, lang, accent, speed, gender, image_style, format, resume=False):
    """Process segments — if resume=True, skip segments that already have a clip.
    Audio is generated sequentially; images are generated in parallel with retry."""
    from video_pipeline.generators import (
        get_tts_generator, get_image_generator, get_video_generator,
        get_image_prompt_generator, use_image_prompt_generation, images_per_segment,
    )

    tts = get_tts_generator()
    img_gen = get_image_generator()
    vid_gen = get_video_generator()
    prompt_gen = get_image_prompt_generator() if use_image_prompt_generation() else None
    workers = int(os.environ.get("IMAGE_GENERATION_WORKERS", "3"))
    num_images = images_per_segment()

    job_id = job.pk

    # Separate segments that need processing vs already done
    done_segs = []
    todo_segs = []
    for seg in segments:
        if resume and seg.clip_path and os.path.exists(seg.clip_path):
            logger.info("[Job %s] Seg %s — skipping (clip already exists)", job_id, seg.order)
            done_segs.append(seg)
        else:
            todo_segs.append(seg)

    logger.info("[Job %s] %d segments to process, %d already done (images_per_segment=%d)",
                job_id, len(todo_segs), len(done_segs), num_images)

    # Step 1: Generate audio sequentially for todo segments
    for seg in todo_segs:
        if _is_stop_requested(job_id):
            raise PipelineStoppedError("Stop requested by user")
        if not seg.audio_path or not os.path.exists(seg.audio_path):
            from video_pipeline.text_sanitizer import sanitize_for_tts
            clean_text = sanitize_for_tts(seg.text)
            logger.info("[Job %s] Seg %s — generating audio...", job_id, seg.order)
            audio_path = tts.generate(
                text=clean_text,
                filename=f"audio_{job_id}_{seg.order}.mp3",
                lang=lang,
                tld=accent,
                speed=speed,
                gender=gender,
            )
            seg.audio_path = audio_path
            seg.save(update_fields=["audio_path"])
            logger.info("[Job %s] Seg %s — audio saved to %s", job_id, seg.order, audio_path)
        else:
            logger.info("[Job %s] Seg %s — audio already exists, skipping", job_id, seg.order)

    # Step 2: Generate images in parallel for segments that don't have all images yet
    def _needs_images(seg):
        existing = seg.get_image_paths()
        return len(existing) < num_images or not all(os.path.exists(p) for p in existing)

    needs_image = [seg for seg in todo_segs if _needs_images(seg)]
    logger.info("[Job %s] %d segments need image generation (workers=%d, %d images each)",
                job_id, len(needs_image), workers, num_images)

    if needs_image:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _generate_images_for_segment,
                    img_gen, prompt_gen, seg, job_id, image_style, format, num_images
                ): seg
                for seg in needs_image
            }
            for future in as_completed(futures):
                order, image_paths = future.result()
                seg = futures[future]
                seg.set_image_paths(image_paths)
                seg.save(update_fields=["image_paths"])
                logger.info("[Job %s] Seg %s — %d images saved", job_id, order, len(image_paths))

                job.completed_segments = len([s for s in segments if s.get_image_paths()])
                job.save(update_fields=["completed_segments", "updated_at"])

    # Step 3: Generate clips sequentially (audio + images both ready)
    order_to_clip = {seg.order: seg.clip_path for seg in done_segs}

    for seg in todo_segs:
        if _is_stop_requested(job_id):
            raise PipelineStoppedError("Stop requested by user")
        logger.info("[Job %s] Seg %s — generating slideshow clip (%d images)...",
                    job_id, seg.order, len(seg.get_image_paths()))
        clip_path = vid_gen.generate_slideshow(
            image_paths=seg.get_image_paths(),
            audio_path=seg.audio_path,
            output_filename=f"clip_{job_id}_{seg.order}.mp4",
            format=format,
        )
        seg.clip_path = clip_path
        seg.save(update_fields=["clip_path"])
        order_to_clip[seg.order] = clip_path
        logger.info("[Job %s] Seg %s — clip saved to %s", job_id, seg.order, clip_path)

        job.completed_segments = len([s for s in segments if s.clip_path])
        job.save(update_fields=["completed_segments", "updated_at"])

    return [order_to_clip[seg.order] for seg in segments]


def _run(job_id: int, story_text: str, lang: str, accent: str, speed: str, gender: str, image_style: str, format: str) -> None:
    """Full pipeline from scratch."""
    _ensure_django()

    from video_pipeline.models import StoryJob, StorySegment
    from video_pipeline.splitter import split_story
    from video_pipeline.generators import get_story_rewriter, use_text_summarization, get_video_generator

    job = StoryJob.objects.get(pk=job_id)
    logger.info("[Job %s] Pipeline started (full run)", job_id)
    _register_stop_event(job_id)

    try:
        # Step 0: Rewrite (optional)
        narration_text = story_text
        if use_text_summarization():
            logger.info("[Job %s] Rewriting story via LLM...", job_id)
            _set_status(job, "rewriting_story")
            narration_text = get_story_rewriter().rewrite(story_text)
            job.rewritten_text = narration_text
            job.save(update_fields=["rewritten_text", "updated_at"])
            _set_status(job, "story_rewritten")
            logger.info("[Job %s] Story rewritten (%d chars)", job_id, len(narration_text))

        # Step 1: Split
        logger.info("[Job %s] Splitting story into segments...", job_id)
        _set_status(job, "splitting_story")
        job.segments.all().delete()
        segments = [
            StorySegment.objects.create(job=job, order=i + 1, text=text)
            for i, text in enumerate(split_story(narration_text))
        ]
        job.total_segments = len(segments)
        job.completed_segments = 0
        job.save(update_fields=["total_segments", "completed_segments", "updated_at"])
        logger.info("[Job %s] Split into %d segments", job_id, len(segments))

        # Step 2: Process segments
        _set_status(job, "processing_segments")
        clip_paths = _process_segments(job, segments, lang, accent, speed, gender, image_style, format, resume=False)

        # Step 3: Merge
        logger.info("[Job %s] Merging %d clips into final video...", job_id, len(clip_paths))
        _set_status(job, "merging_video")
        video_path = get_video_generator().concat(
            clip_paths=clip_paths,
            output_filename=f"video_{job_id}.mp4",
        )
        job.video_path = video_path
        job.status = "done"
        job.save(update_fields=["status", "video_path", "updated_at"])
        logger.info("[Job %s] Done — video at %s", job_id, video_path)

    except PipelineStoppedError:
        logger.info("[Job %s] Pipeline stopped by user", job_id)
        job.status = "stopped"
        job.error_message = ""
        job.save(update_fields=["status", "error_message", "updated_at"])

    except Exception as exc:
        logger.exception("[Job %s] Pipeline failed: %s", job_id, exc)
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message", "updated_at"])

    finally:
        _unregister_stop_event(job_id)


def _resume(job_id: int, lang: str, accent: str, speed: str, gender: str, image_style: str, format: str) -> None:
    """Smart resume — skips completed segments, continues from where it failed."""
    _ensure_django()

    from video_pipeline.models import StoryJob, StorySegment
    from video_pipeline.splitter import split_story
    from video_pipeline.generators import get_story_rewriter, use_text_summarization, get_video_generator

    job = StoryJob.objects.get(pk=job_id)
    logger.info("[Job %s] Pipeline resumed", job_id)
    _register_stop_event(job_id)

    try:
        # Step 0: Rewrite only if not already done
        narration_text = job.rewritten_text or job.story_text
        if not job.rewritten_text and use_text_summarization():
            logger.info("[Job %s] Rewriting story via LLM...", job_id)
            _set_status(job, "rewriting_story")
            narration_text = get_story_rewriter().rewrite(job.story_text)
            job.rewritten_text = narration_text
            job.save(update_fields=["rewritten_text", "updated_at"])
            _set_status(job, "story_rewritten")
            logger.info("[Job %s] Story rewritten (%d chars)", job_id, len(narration_text))

        # Step 1: Split only if no segments exist
        segments = list(job.segments.order_by("order"))
        if not segments:
            logger.info("[Job %s] No segments found, splitting story...", job_id)
            _set_status(job, "splitting_story")
            segments = [
                StorySegment.objects.create(job=job, order=i + 1, text=text)
                for i, text in enumerate(split_story(narration_text))
            ]
            job.total_segments = len(segments)
            job.completed_segments = 0
            job.save(update_fields=["total_segments", "completed_segments", "updated_at"])
            logger.info("[Job %s] Split into %d segments", job_id, len(segments))
        else:
            logger.info("[Job %s] Found %d existing segments", job_id, len(segments))

        # Step 2: Process segments — skip ones that already have clips
        _set_status(job, "processing_segments")
        clip_paths = _process_segments(job, segments, lang, accent, speed, gender, image_style, format, resume=True)

        # Step 3: Merge
        logger.info("[Job %s] Merging %d clips into final video...", job_id, len(clip_paths))
        _set_status(job, "merging_video")
        video_path = get_video_generator().concat(
            clip_paths=clip_paths,
            output_filename=f"video_{job_id}.mp4",
        )
        job.video_path = video_path
        job.status = "done"
        job.save(update_fields=["status", "video_path", "updated_at"])
        logger.info("[Job %s] Done — video at %s", job_id, video_path)

    except PipelineStoppedError:
        logger.info("[Job %s] Pipeline stopped by user", job_id)
        job.status = "stopped"
        job.error_message = ""
        job.save(update_fields=["status", "error_message", "updated_at"])

    except Exception as exc:
        logger.exception("[Job %s] Pipeline failed: %s", job_id, exc)
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message", "updated_at"])

    finally:
        _unregister_stop_event(job_id)


def run_pipeline_async(job_id: int, story_text: str, lang: str, accent: str, speed: str, gender: str, image_style: str = "cartoon", format: str = "normal") -> None:
    """Start full pipeline from scratch in background thread."""
    thread = threading.Thread(target=_run, args=(job_id, story_text, lang, accent, speed, gender, image_style, format), daemon=True)
    thread.start()


def resume_pipeline_async(job_id: int, lang: str, accent: str, speed: str, gender: str, image_style: str = "cartoon", format: str = "normal") -> None:
    """Smart resume pipeline in background thread."""
    thread = threading.Thread(target=_resume, args=(job_id, lang, accent, speed, gender, image_style, format), daemon=True)
    thread.start()
