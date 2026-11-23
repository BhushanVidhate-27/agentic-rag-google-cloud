"""Run transparent dataset checks. Requires an already running API and ingested files."""

import argparse
import json
import os
import urllib.request
from pathlib import Path


def evaluate(dataset: Path, base_url: str, api_key: str) -> dict:
    if not api_key:
        raise ValueError("Set API_ACCESS_KEY before evaluation")
    records = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    retrieval_hits = 0
    answer_hits = 0
    for record in records:
        request = urllib.request.Request(
            base_url.rstrip("/") + "/v1/ask",
            data=json.dumps({"question": record["question"]}).encode(),
            headers={"Content-Type": "application/json", "X-API-Key": api_key},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.load(response)
        sources = [source["source"] for source in result.get("sources", [])]
        retrieval_hits += int(record["expected_source"] in sources)
        answer_hits += int(
            record["expected_phrase"].lower() in result.get("answer", "").lower()
        )
        print(json.dumps({"question": record["question"], "sources": sources,
                          "contains_expected_phrase": bool(
                              record["expected_phrase"].lower()
                              in result.get("answer", "").lower()
                          )}))
    count = len(records)
    return {"questions": count, "source_hit_rate": retrieval_hits / count if count else 0,
            "answer_substring_accuracy": answer_hits / count if count else 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.dataset, args.base_url, os.getenv("API_ACCESS_KEY", "")),
                     indent=2))
