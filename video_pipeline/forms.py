from django import forms
from .models import TTSSettings


class GenerateStoryForm(forms.Form):
    story_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 8, "style": "width:100%"}),
        label="Story Text",
    )
    lang = forms.ChoiceField(choices=TTSSettings.LANG_CHOICES, label="Language")
    accent = forms.ChoiceField(choices=TTSSettings.ACCENT_CHOICES, label="Accent / Region")
    speed = forms.ChoiceField(choices=TTSSettings.SPEED_CHOICES, label="Speed")
    voice_gender = forms.ChoiceField(choices=TTSSettings.VOICE_GENDER_CHOICES, label="Voice Gender")
    image_style = forms.ChoiceField(choices=TTSSettings.IMAGE_STYLE_CHOICES, label="Image Style")
    format = forms.ChoiceField(choices=TTSSettings.FORMAT_CHOICES, label="Format")
