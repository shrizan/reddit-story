"""
Sanitize text before sending to TTS.
Strips Reddit/markdown formatting, HTML entities, and characters
that cause edge-tts (and gTTS) to produce silence or errors.
"""

import html
import re


def sanitize_for_tts(text: str) -> str:
    # Decode HTML entities (&amp; &quot; &#39; etc.)
    text = html.unescape(text)

    # Strip markdown links — keep the display text, drop the URL
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Strip bare URLs
    text = re.sub(r'https?://\S+', '', text)

    # Strip bold/italic markdown (**, __, *, _)
    text = re.sub(r'\*{1,3}|_{1,3}', '', text)

    # Strip strikethrough ~~text~~
    text = re.sub(r'~~(.+?)~~', r'\1', text)

    # Strip inline code `code`
    text = re.sub(r'`[^`]*`', '', text)

    # Convert Reddit username/subreddit mentions to speakable form
    text = re.sub(r'\bu/(\w+)', r'user \1', text)
    text = re.sub(r'\br/(\w+)', r'the \1 subreddit', text)

    # Replace em dash and en dash with a comma pause
    text = re.sub(r'[—–]', ', ', text)

    # Replace ellipsis characters and triple dots with a period
    text = re.sub(r'\.{3,}|…', '.', text)

    # Remove emojis and other non-BMP unicode (most emoji are U+1F000 and above)
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)

    # Remove other common unicode symbols that TTS engines skip
    text = re.sub(r'[★☆♡♥♦♣♠•◦▪▸►◄◀▶→←↑↓]', '', text)

    # Replace & with "and"
    text = re.sub(r'\s*&\s*', ' and ', text)

    # Collapse multiple spaces/newlines into a single space
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n+', ' ', text)

    return text.strip()
