"""Tests for FastAPI HTTP endpoints including POST /ask and GET /health."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.models.response import AskResponse


@pytest.fixture
def mock_service():
    service = AsyncMock()
    service.answer_question.return_value = AskResponse(
        answer="According to the Superhero API, Batman is Bruce Wayne. Based on the Mythology Dataset, Achilles was a Greek hero.",
        sources=["Superhero API (Batman)", "Text Dataset (achilles_trojan_war.txt)"],
        route="both",
        retrieved_superheroes=["Batman"],
        retrieved_documents=["achilles_trojan_war.txt"],
        latency_ms=120.5,
        llm_provider="Groq (llama-3.3-70b-versatile)",
    )
    return service


@pytest.mark.asyncio
async def test_ask_endpoint_success(mock_service):
    app.dependency_overrides = {}
    from app.main import get_service
    app.dependency_overrides[get_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/ask", json={"question": "Compare Batman to Achilles"})

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) == 2
    assert data["route"] == "both"
    assert data["latency_ms"] == 120.5

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ask_endpoint_empty_question_validation_error():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Empty string
        res1 = await client.post("/ask", json={"question": ""})
        assert res1.status_code == 422

        # Whitespace only
        res2 = await client.post("/ask", json={"question": "    "})
        assert res2.status_code == 422

        # Missing body field
        res3 = await client.post("/ask", json={})
        assert res3.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "superhero_api_configured" in data
    assert "llm_configured" in data


@pytest.mark.asyncio
async def test_root_serves_html():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "Nexus AI Chatbot" in response.text or "AI Engineer Chatbot" in response.text
