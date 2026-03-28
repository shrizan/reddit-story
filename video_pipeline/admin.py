import os
from django.contrib import admin, messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .forms import GenerateStoryForm
from .models import StoryJob, StorySegment, TTSSettings
from .pipeline import run_pipeline_async, resume_pipeline_async, request_stop


class StorySegmentInline(admin.TabularInline):
    model = StorySegment
    extra = 0
    readonly_fields = ("order", "short_text", "audio_done", "image_done", "clip_done")
    fields = ("order", "short_text", "audio_done", "image_done", "clip_done")
    can_delete = False
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Text")
    def short_text(self, obj):
        return obj.text[:80] + "…" if len(obj.text) > 80 else obj.text

    @admin.display(description="Audio")
    def audio_done(self, obj):
        return "✓" if obj.audio_path else "—"

    @admin.display(description="Image")
    def image_done(self, obj):
        return "✓" if obj.image_path else "—"

    @admin.display(description="Clip")
    def clip_done(self, obj):
        return "✓" if obj.clip_path else "—"


@admin.register(TTSSettings)
class TTSSettingsAdmin(admin.ModelAdmin):
    list_display = ("lang", "accent", "speed", "voice_gender", "image_style", "format")
    fields = ("lang", "accent", "speed", "voice_gender", "image_style", "format")

    def has_add_permission(self, request):
        return not TTSSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        settings_obj = TTSSettings.get_defaults()
        return redirect(
            reverse("admin:video_pipeline_ttssettings_change", args=[settings_obj.pk])
        )


@admin.register(StoryJob)
class StoryJobAdmin(admin.ModelAdmin):
    list_display = ("short_story", "lang", "accent", "speed", "voice_gender", "image_style", "format", "status_badge", "created_at", "download_button")
    list_filter = ("status", "lang", "image_style", "format")
    inlines = [StorySegmentInline]

    fieldsets = (
        ("Story", {
            "fields": ("story_text", "rewritten_text"),
        }),
        ("TTS Options", {
            "fields": ("lang", "accent", "speed", "voice_gender"),
        }),
        ("Image Options", {
            "fields": ("image_style", "format"),
        }),
        ("Pipeline Status", {
            "fields": ("status", "total_segments", "completed_segments", "error_message"),
        }),
        ("Output", {
            "fields": ("video_path",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    readonly_fields = (
        "rewritten_text", "status", "total_segments", "completed_segments",
        "video_path", "error_message", "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("generate/", self.admin_site.admin_view(self.generate_view), name="storyjob_generate"),
            path("<int:job_id>/download/", self.admin_site.admin_view(self.download_view), name="storyjob_download"),
            path("<int:job_id>/regenerate/", self.admin_site.admin_view(self.regenerate_view), name="storyjob_regenerate"),
            path("<int:job_id>/resume/", self.admin_site.admin_view(self.resume_view), name="storyjob_resume"),
            path("<int:job_id>/stop/", self.admin_site.admin_view(self.stop_view), name="storyjob_stop"),
        ]
        return custom + urls

    # ------------------------------------------------------------------ views

    def generate_view(self, request):
        defaults = TTSSettings.get_defaults()

        if request.method == "POST":
            form = GenerateStoryForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data

                job = StoryJob.objects.create(
                    story_text=data["story_text"],
                    lang=data["lang"],
                    accent=data["accent"],
                    speed=data["speed"],
                    voice_gender=data["voice_gender"],
                    image_style=data["image_style"],
                    format=data["format"],
                    status="pending",
                )

                run_pipeline_async(
                    job_id=job.pk,
                    story_text=job.story_text,
                    lang=job.lang,
                    accent=job.accent,
                    speed=job.speed,
                    gender=job.voice_gender,
                    image_style=job.image_style,
                    format=job.format,
                )

                messages.success(request, f"Story job #{job.pk} started. Refresh the list to see progress.")
                return redirect(reverse("admin:video_pipeline_storyjob_changelist"))
        else:
            form = GenerateStoryForm(initial={
                "lang": defaults.lang,
                "accent": defaults.accent,
                "speed": defaults.speed,
                "voice_gender": defaults.voice_gender,
                "image_style": defaults.image_style,
                "format": defaults.format,
            })

        context = {
            **self.admin_site.each_context(request),
            "title": "Generate Story Video",
            "form": form,
        }
        return render(request, "admin/video_pipeline/generate_story.html", context)

    def regenerate_view(self, request, job_id):
        try:
            job = StoryJob.objects.get(pk=job_id)
        except StoryJob.DoesNotExist:
            raise Http404

        job.status = "pending"
        job.error_message = ""
        job.video_path = ""
        job.rewritten_text = ""
        job.total_segments = 0
        job.completed_segments = 0
        job.save(update_fields=[
            "status", "error_message", "video_path",
            "rewritten_text", "total_segments", "completed_segments", "updated_at"
        ])

        run_pipeline_async(
            job_id=job.pk,
            story_text=job.story_text,
            lang=job.lang,
            accent=job.accent,
            speed=job.speed,
            gender=job.voice_gender,
            image_style=job.image_style,
            format=job.format,
        )

        messages.success(request, f"Story job #{job.pk} queued for regeneration.")
        return redirect(reverse("admin:video_pipeline_storyjob_changelist"))

    def resume_view(self, request, job_id):
        try:
            job = StoryJob.objects.get(pk=job_id)
        except StoryJob.DoesNotExist:
            raise Http404

        job.status = "pending"
        job.error_message = ""
        job.video_path = ""
        job.save(update_fields=["status", "error_message", "video_path", "updated_at"])

        resume_pipeline_async(
            job_id=job.pk,
            lang=job.lang,
            accent=job.accent,
            speed=job.speed,
            gender=job.voice_gender,
            image_style=job.image_style,
            format=job.format,
        )

        messages.success(request, f"Story job #{job.pk} resuming from last checkpoint.")
        return redirect(reverse("admin:video_pipeline_storyjob_changelist"))

    def stop_view(self, request, job_id):
        try:
            job = StoryJob.objects.get(pk=job_id)
        except StoryJob.DoesNotExist:
            raise Http404

        request_stop(job_id)
        messages.warning(request, f"Stop signal sent to job #{job_id}. It will halt after the current segment.")
        return redirect(reverse("admin:video_pipeline_storyjob_changelist"))

    def download_view(self, request, job_id):
        try:
            job = StoryJob.objects.get(pk=job_id)
        except StoryJob.DoesNotExist:
            raise Http404

        if not job.is_downloadable or not os.path.exists(job.video_path):
            raise Http404("Video file not found.")

        return FileResponse(
            open(job.video_path, "rb"),
            as_attachment=True,
            filename=f"story_{job_id}.mp4",
        )

    # --------------------------------------------------------- display helpers

    @admin.display(description="Story")
    def short_story(self, obj):
        text = obj.story_text
        return text[:70] + "…" if len(text) > 70 else text

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "pending":              "#888888",
            "rewriting_story":      "#20a0a0",
            "story_rewritten":      "#48c2c2",
            "splitting_story":      "#7a6fc4",
            "processing_segments":  "#1a6fc4",
            "merging_video":        "#e6a817",
            "done":                 "#28a745",
            "stopped":              "#fd7e14",
            "failed":               "#dc3545",
        }
        color = colors.get(obj.status, "#888")
        label = obj.get_status_display()
        if obj.status == "processing_segments" and obj.total_segments:
            label = f"Processing ({obj.completed_segments}/{obj.total_segments})"

        return format_html(
            '<span style="color:white;background:{};padding:2px 10px;border-radius:4px;'
            'font-size:11px;white-space:nowrap">{}</span>',
            color,
            label,
        )

    @admin.display(description="Actions")
    def download_button(self, obj):
        in_progress_statuses = {
            "pending", "rewriting_story", "story_rewritten",
            "splitting_story", "processing_segments", "merging_video",
        }

        if obj.is_downloadable:
            url = reverse("admin:storyjob_download", args=[obj.pk])
            return format_html(
                '<a href="{}" style="display:inline-block;padding:4px 12px;'
                'background:#28a745;color:white;border-radius:4px;font-size:12px;'
                'font-weight:bold;text-decoration:none;">Download</a>',
                url,
            )

        if obj.status in in_progress_statuses:
            stop_url = reverse("admin:storyjob_stop", args=[obj.pk])
            return format_html(
                '<a href="{}" style="display:inline-block;padding:4px 10px;'
                'background:#fd7e14;color:white;border-radius:4px;font-size:11px;'
                'font-weight:bold;text-decoration:none;">Stop</a>',
                stop_url,
            )

        if obj.status in ("failed", "stopped"):
            resume_url = reverse("admin:storyjob_resume", args=[obj.pk])
            reset_url = reverse("admin:storyjob_regenerate", args=[obj.pk])
            return format_html(
                '<a href="{}" style="display:inline-block;padding:4px 10px;'
                'background:#1a6fc4;color:white;border-radius:4px;font-size:11px;'
                'font-weight:bold;text-decoration:none;margin-right:4px;">Resume</a>'
                '<a href="{}" style="display:inline-block;padding:4px 10px;'
                'background:#dc3545;color:white;border-radius:4px;font-size:11px;'
                'font-weight:bold;text-decoration:none;">Reset & Redo</a>',
                resume_url,
                reset_url,
            )

        return "—"

    def changelist_view(self, request, extra_context=None):
        in_progress = [
            "pending", "rewriting_story", "story_rewritten",
            "splitting_story", "processing_segments", "merging_video",
        ]
        has_active = StoryJob.objects.filter(status__in=in_progress).exists()
        extra_context = extra_context or {}
        extra_context["auto_refresh"] = has_active
        return super().changelist_view(request, extra_context=extra_context)
