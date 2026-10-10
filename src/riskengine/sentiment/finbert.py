import hashlib
import json

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.riskengine.config import DATA_DIR, load_yaml
from src.riskengine.models import SentimentResult
from src.riskengine.sentiment.base import label_for, neutral_band


def text_key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


class FinbertSentiment:
    def __init__(self) -> None:
        settings = load_yaml("normalization.yaml")["finbert"]
        torch.manual_seed(0)
        self.device = "cpu"
        self.batch_size = settings["batch_size"]
        self.max_length = settings["max_length"]
        self.tokenizer = AutoTokenizer.from_pretrained(settings["model_id"], revision=settings["revision"])
        self.model = AutoModelForSequenceClassification.from_pretrained(settings["model_id"], revision=settings["revision"]).to(self.device).eval()
        labels = {name.lower(): index for index, name in self.model.config.id2label.items()}
        self.positive_index = labels["positive"]
        self.negative_index = labels["negative"]
        self.name = f"finbert@{settings['revision'][:7]}"
        self.band = neutral_band("finbert")
        self.cache_path = DATA_DIR / "raw" / f"finbert_{settings['revision'][:7]}_cache.json"
        self.cache = json.loads(self.cache_path.read_text(encoding="utf-8")) if self.cache_path.exists() else {}

    def raw_scores(self, texts: list[str]) -> list[float]:
        scores = []
        with torch.inference_mode():
            for offset in range(0, len(texts), self.batch_size):
                batch = self.tokenizer(texts[offset:offset + self.batch_size], padding=True, truncation=True, max_length=self.max_length, return_tensors="pt").to(self.device)
                probabilities = torch.softmax(self.model(**batch).logits.float(), dim=-1).cpu()
                scores += [round(float(row[self.positive_index] - row[self.negative_index]), 4) for row in probabilities]
        return scores

    def score(self, texts: list[str]) -> list[SentimentResult]:
        keys = [text_key(t) for t in texts]
        missing = sorted({k: t for k, t in zip(keys, texts) if k not in self.cache}.items())
        if missing:
            for (key, _), value in zip(missing, self.raw_scores([t for _, t in missing])):
                self.cache[key] = value
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache, sort_keys=True), encoding="utf-8")
        return [SentimentResult(score=self.cache[k], label=label_for(self.cache[k], self.band), model=self.name) for k in keys]
