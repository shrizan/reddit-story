import re


def split_story(text: str, min_words: int = 25, max_words: int = 80) -> list[str]:
    """
    Split story text into narration segments.

    Strategy:
    - Split on paragraph breaks first
    - Merge short paragraphs (< min_words) with the next
    - Split long paragraphs (> max_words) at sentence boundaries
    - Target: 25–80 words per segment → typically 5–10 segments
    """
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    segments = []
    buffer = []
    buffer_words = 0

    def flush(buf):
        return " ".join(buf).strip()

    for para in paragraphs:
        word_count = len(para.split())

        if word_count > max_words:
            # Flush current buffer first
            if buffer:
                segments.append(flush(buffer))
                buffer = []
                buffer_words = 0

            # Split long paragraph at sentence boundaries
            sentences = re.split(r'(?<=[.!?])\s+', para)
            sent_buf = []
            sent_words = 0

            for sent in sentences:
                sw = len(sent.split())
                if sent_words + sw > max_words and sent_buf:
                    segments.append(flush(sent_buf))
                    sent_buf = [sent]
                    sent_words = sw
                else:
                    sent_buf.append(sent)
                    sent_words += sw

            if sent_buf:
                if sent_words < min_words:
                    buffer = sent_buf
                    buffer_words = sent_words
                else:
                    segments.append(flush(sent_buf))

        elif buffer_words + word_count > max_words:
            if buffer:
                segments.append(flush(buffer))
            buffer = [para]
            buffer_words = word_count

        else:
            buffer.append(para)
            buffer_words += word_count

            if buffer_words >= min_words:
                segments.append(flush(buffer))
                buffer = []
                buffer_words = 0

    # Flush remaining into last segment
    if buffer:
        if segments:
            segments[-1] = segments[-1] + " " + flush(buffer)
        else:
            segments.append(flush(buffer))

    return [s for s in segments if s]
