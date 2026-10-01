"""Tests for SuperheroAPIClient with mocked HTTP responses."""

import httpx
import pytest
from app.services.superhero_client import SuperheroAPIClient


@pytest.fixture
def client():
    return SuperheroAPIClient(token="mock_token_123")


@pytest.mark.asyncio
async def test_search_character_unconfigured():
    unconfigured_client = SuperheroAPIClient(token="")
    results = await unconfigured_client.search_character("batman")
    assert results == []


@pytest.mark.asyncio
async def test_search_character_empty_name(client):
    results = await client.search_character("")
    assert results == []


@pytest.mark.asyncio
async def test_search_character_success(monkeypatch, client):
    mock_payload = {
        "response": "success",
        "results-for": "batman",
        "results": [
            {
                "id": "70",
                "name": "Batman",
                "powerstats": {
                    "intelligence": "100",
                    "strength": "26",
                    "speed": "27",
                    "durability": "50",
                    "power": "47",
                    "combat": "100",
                },
                "biography": {
                    "full-name": "Bruce Wayne",
                    "alter-egos": "No alter egos found.",
                    "aliases": ["Insider", "Matches Malone"],
                    "place-of-birth": "Gotham City",
                    "first-appearance": "Detective Comics #27",
                    "publisher": "DC Comics",
                    "alignment": "good",
                },
                "appearance": {
                    "gender": "Male",
                    "race": "Human",
                    "height": ["6'2", "188 cm"],
                    "weight": ["210 lb", "95 kg"],
                },
                "work": {
                    "occupation": "Businessman",
                },
                "connections": {
                    "group-affiliation": "Justice League, Batman Family",
                },
            }
        ],
    }

    async def mock_get(self, url, *args, **kwargs):
        return httpx.Response(200, json=mock_payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    results = await client.search_character("batman")
    assert len(results) == 1
    batman = results[0]
    assert batman.name == "Batman"
    assert batman.full_name == "Bruce Wayne"
    assert batman.powerstats["intelligence"] == "100"
    assert "DC Comics" in batman.publisher
    context_str = batman.to_context_string()
    assert "Bruce Wayne" in context_str
    assert "Intelligence: 100" in context_str


@pytest.mark.asyncio
async def test_search_character_not_found(monkeypatch, client):
    mock_payload = {
        "response": "error",
        "error": "character with given name not found",
    }

    async def mock_get(self, url, *args, **kwargs):
        return httpx.Response(200, json=mock_payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    results = await client.search_character("nonexistentcharacter999")
    assert results == []


@pytest.mark.asyncio
async def test_search_character_http_error(monkeypatch, client):
    async def mock_get(self, url, *args, **kwargs):
        return httpx.Response(500, text="Internal Server Error", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    results = await client.search_character("superman")
    assert results == []
