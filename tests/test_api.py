"""Security boundary tests without Gemini or Chroma network requests."""

from fastapi.testclient import TestClient

from agentic_rag.api import app, get_settings
from agentic_rag.config import Settings


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_unauthorized_upload_and_question():
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_access_key="test-access-key"
    )
    try:
        with TestClient(app) as client:
            response = client.post("/v1/ask", json={"question": "hello"})
            assert response.status_code == 401
            response = client.post(
                "/v1/documents",
                files={"file": ("x.txt", b"hello", "text/plain")},
            )
            assert response.status_code == 401
            response = client.post(
                "/v1/ask",
                headers={"X-API-Key": "wrong"},
                json={"question": "hello"},
            )
            assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_missing_configured_key_fails_closed():
    app.dependency_overrides[get_settings] = lambda: Settings(api_access_key="")
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/ask",
                headers={"X-API-Key": "anything"},
                json={"question": "hello"},
            )
            assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
