from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


client = TestClient(app)


def test_root_serves_enterprise_ui() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Financial RAG" in response.text


def test_health_is_public() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_documents_require_api_key() -> None:
    response = client.get("/api/v1/documents")

    assert response.status_code == 401


def test_documents_accept_valid_api_key() -> None:
    response = client.get(
        "/api/v1/documents",
        headers={"X-API-Key": get_settings().api_key},
    )

    assert response.status_code == 200
    assert "documents" in response.json()
