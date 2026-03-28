from .base import BaseStoryRewriter

MODEL_NAME = "sshleifer/distilbart-cnn-12-6"


class FalconsaiRewriter(BaseStoryRewriter):
    """
    Story rewriter using Falconsai/text_summarization (fine-tuned T5).
    Model is downloaded on first use and cached locally by HuggingFace.
    """

    _tokenizer = None
    _model = None

    def _load(self):
        if self._model is None:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            self.__class__._tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self.__class__._model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

    def rewrite(self, text: str) -> str:
        self._load()

        # T5 works best under 512 tokens — trim if needed
        words = text.split()
        if len(words) > 400:
            text = " ".join(words[:400])

        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
        )

        output_ids = self._model.generate(
            inputs["input_ids"],
            max_new_tokens=300,
            min_new_tokens=80,
            num_beams=4,
            early_stopping=True,
        )

        return self._tokenizer.decode(output_ids[0], skip_special_tokens=True)
