"""Public demo must remain credential-free and unable to access private endpoints."""

from fastapi.testclient import TestClient

from agentic_rag.api import app, get_settings
from agentic_rag.config import Settings
from agentic_rag.demo import demo_answer


def test_sample_question_is_extractive():
    result = demo_answer("Who coordinates a P1 incident?")
    assert result["demo"] is True
    assert result["model_used"] is False
    assert result["sources"]
    assert result["sources"][0]["source"] == "handbook.txt"
    assert "[S1]" in result["answer"]


def test_unrelated_question_abstains():
    result = demo_answer("quantum banana zeppelin")
    assert result["sources"] == []
    assert "No matching evidence" in result["answer"]


def test_demo_is_public_but_data_api_is_blocked():
    app.dependency_overrides[get_settings] = lambda: Settings(demo_mode=True)
    try:
        with TestClient(app) as client:
            assert client.get("/").status_code == 200
            assert "Safe public preview" in client.get("/").text
            answer = client.post("/demo/ask", json={"question": "What is the security policy?"})
            assert answer.status_code == 200
            assert answer.json()["model_used"] is False
            assert client.post("/v1/ask", json={"question": "hello"}).status_code == 403
            assert client.post(
                "/v1/documents", files={"file": ("test.txt", b"secret")}
            ).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_demo_route_disabled_in_private_mode():
    app.dependency_overrides[get_settings] = lambda: Settings(demo_mode=False)
    try:
        with TestClient(app) as client:
            assert client.post("/demo/ask", json={"question": "hello"}).status_code == 404
    finally:
        app.dependency_overrides.clear()
