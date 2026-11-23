"""Safe public preview with fictional sample data and no external API calls.

This endpoint intentionally does not invoke Gemini, write vectors, accept uploads,
or expose protected /v1 endpoints. It is a retrieval preview, not a live AI model.
"""

import re
from pathlib import Path

from pydantic import BaseModel, Field

from agentic_rag.vector_store import Evidence

SAMPLE_PATH = Path(__file__).resolve().parents[2] / "examples" / "handbook.txt"

# Fixed, fictional answers; no uncontrolled Gemini API usage in a public preview.
FAQ = (
    ("p1", "The on-call incident commander coordinates a P1 incident.", "incident response"),
    ("incident", "The on-call incident commander coordinates a P1 incident.", "incident response"),
    ("update", "The communications lead posts customer updates every thirty minutes.", "incident response"),
    ("security", "Employees must use multifactor authentication on production accounts.", "security"),
    ("authentication", "Employees must use multifactor authentication on production accounts.", "security"),
    ("onboard", "Knowledge base access follows manager approval.", "onboarding"),
    ("access", "Knowledge base access follows manager approval.", "onboarding"),
    ("escalat", "After thirty minutes, the incident commander pages the infrastructure lead.", "escalation"),
    ("support", "Support acknowledges customer requests within one business day.", "support"),
)


class DemoQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=300)


def sample_sections() -> list[tuple[str, str]]:
    text = SAMPLE_PATH.read_text(encoding="utf-8")
    return [
        (line.split(":", 1)[0].strip().lower(), line.strip())
        for line in text.splitlines()
        if ":" in line
    ]


def demo_answer(question: str) -> dict:
    query = question.lower()
    sections = sample_sections()
    # Deterministic keyword retrieval: no LLM, no API key, no billing.
    tokens = set(re.findall(r"[a-z0-9]+", query))
    stop = {"what", "when", "where", "which", "does", "the", "this", "that", "with",
            "from", "have", "about", "are", "how", "who", "and", "for", "can", "you"}
    keywords = tokens - stop
    scored = []
    for index, (title, text) in enumerate(sections):
        words = set(re.findall(r"[a-z0-9]+", text.lower()))
        score = len(keywords & words)
        if score:
            scored.append((score, index, title, text))
    scored.sort(key=lambda item: (-item[0], item[1]))
    if not scored:
        return {
            "answer": "No matching evidence was found in the fictional sample handbook.",
            "route": "sample_keyword_retrieval",
            "sources": [],
            "tokens": None,
            "demo": True,
            "model_used": False,
        }
    _, index, title, excerpt = scored[0]
    # An extractive answer is safe and faithful to the sample.
    evidence = Evidence(source="handbook.txt", chunk_index=index, text=excerpt, distance=None)
    return {
        "answer": f"{excerpt} [S1]",
        "route": "sample_keyword_retrieval",
        "sources": [{
            "id": "S1", "source": evidence.source, "chunk_index": evidence.chunk_index,
            "text": evidence.text, "distance": evidence.distance,
        }],
        "tokens": None,
        "demo": True,
        "model_used": False,
    }
