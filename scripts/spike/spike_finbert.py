import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_ID = "ProsusAI/finbert"
REVISION = "4556d13015211d73dccd3fdd39d39232506f3e43"
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "spike_finbert.json"
SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "spike_gdelt_W1.json"
TARGET_ITEMS = 1000
BATCH_SIZE = 32


def load_headlines() -> list[str]:
    report = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    titles = [e["title"] for window in report.values() for s in window["samples"] for e in s.get("examples", [])]
    seed = titles or ["Stocks fall as Russia invades Ukraine", "Fed raises rates by 25 basis points"]
    return (seed * (TARGET_ITEMS // len(seed) + 1))[:TARGET_ITEMS]


def time_device(device: str, headlines: list[str]) -> dict:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, revision=REVISION).to(device).eval()
    started = time.perf_counter()
    with torch.inference_mode():
        for offset in range(0, len(headlines), BATCH_SIZE):
            batch = tokenizer(headlines[offset:offset + BATCH_SIZE], padding=True, truncation=True, max_length=64, return_tensors="pt").to(device)
            model(**batch)
    elapsed = time.perf_counter() - started
    return {"device": device, "items": len(headlines), "seconds": round(elapsed, 2), "items_per_second": round(len(headlines) / elapsed, 1), "labels": model.config.id2label}


def main() -> None:
    headlines = load_headlines()
    results = [time_device("cpu", headlines)]
    if torch.cuda.is_available():
        results.append(time_device("cuda", headlines))
    OUTPUT_PATH.write_text(json.dumps({"torch": torch.__version__, "cuda_available": torch.cuda.is_available(), "results": results}, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
