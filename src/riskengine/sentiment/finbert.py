import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.riskengine.config import load_yaml
from src.riskengine.models import SentimentResult
from src.riskengine.sentiment.base import label_for


class FinbertSentiment:
    def __init__(self) -> None:
        settings = load_yaml("normalization.yaml")["finbert"]
        torch.manual_seed(0)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.batch_size = settings["batch_size"]
        self.max_length = settings["max_length"]
        self.tokenizer = AutoTokenizer.from_pretrained(settings["model_id"], revision=settings["revision"])
        self.model = AutoModelForSequenceClassification.from_pretrained(settings["model_id"], revision=settings["revision"]).to(self.device).eval()
        labels = {name.lower(): index for index, name in self.model.config.id2label.items()}
        self.positive_index = labels["positive"]
        self.negative_index = labels["negative"]
        self.name = f"finbert@{settings['revision'][:7]}"

    def score(self, texts: list[str]) -> list[SentimentResult]:
        results = []
        with torch.inference_mode():
            for offset in range(0, len(texts), self.batch_size):
                batch = self.tokenizer(texts[offset:offset + self.batch_size], padding=True, truncation=True, max_length=self.max_length, return_tensors="pt").to(self.device)
                probabilities = torch.softmax(self.model(**batch).logits.float(), dim=-1).cpu()
                for row in probabilities:
                    value = round(float(row[self.positive_index] - row[self.negative_index]), 4)
                    results.append(SentimentResult(score=value, label=label_for(value), model=self.name))
        return results
