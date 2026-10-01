"""Tests for ChatbotService domain orchestrator."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from app.config import Settings
from app.models.request import AskRequest
from app.services.chatbot_service import ChatbotService
from app.services.dataset_retriever import DocumentResult
from app.services.router import RoutingDecision
from app.services.superhero_client import SuperheroData


@pytest.fixture
def mock_settings(tmp_path):
    return Settings(
        superhero_api_token="test_token",
        dataset_dir="data/mythology_and_legends",
        llm_provider="groq",
        groq_api_key="test_key",
    )


@pytest.mark.asyncio
async def test_chatbot_service_superhero_route(mock_settings):
    mock_router = MagicMock()
    mock_router.route_with_llm_or_fallback = AsyncMock(
        return_value=RoutingDecision(
            route="superhero",
            superhero_names=["iron man"],
            dataset_keywords="",
            reasoning="Testing superhero route",
        )
    )

    mock_hero = SuperheroData(
        id="346",
        name="Iron Man",
        full_name="Tony Stark",
        alter_egos="No",
        aliases=[],
        publisher="Marvel Comics",
        alignment="good",
        first_appearance="Tales of Suspense #39",
        powerstats={"intelligence": "100", "strength": "85"},
        gender="Male",
        race="Human",
        height="6'6",
        weight="425 lb",
        work_occupation="Inventor",
        connections_group="Avengers",
    )

    mock_superhero_client = MagicMock()
    mock_superhero_client.is_configured.return_value = True
    mock_superhero_client.search_character = AsyncMock(return_value=[mock_hero])

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = []

    mock_llm = MagicMock()
    mock_llm.is_configured.return_value = True
    mock_llm.provider_name = "Groq (llama-3.3-70b-versatile)"
    mock_llm.generate = AsyncMock(
        return_value="According to the Superhero API, Iron Man is Tony Stark, an inventor with an intelligence rating of 100."
    )

    service = ChatbotService(
        settings=mock_settings,
        router=mock_router,
        dataset_retriever=mock_retriever,
        superhero_client=mock_superhero_client,
        llm_client=mock_llm,
    )

    request = AskRequest(question="Who is Iron Man?")
    response = await service.answer_question(request)

    assert response.route == "superhero"
    assert "Superhero API (Iron Man)" in response.sources
    assert "Tony Stark" in response.answer
    assert response.retrieved_superheroes == ["Iron Man"]
    assert response.latency_ms is not None
    assert response.latency_ms > 0
    mock_superhero_client.search_character.assert_called_once_with("iron man")
    mock_retriever.search.assert_not_called()


@pytest.mark.asyncio
async def test_chatbot_service_dataset_route(mock_settings):
    mock_router = MagicMock()
    mock_router.route_with_llm_or_fallback = AsyncMock(
        return_value=RoutingDecision(
            route="dataset",
            superhero_names=[],
            dataset_keywords="Thor Norse",
            reasoning="Testing dataset route",
        )
    )

    mock_superhero_client = MagicMock()
    mock_superhero_client.is_configured.return_value = True
    mock_superhero_client.search_character = AsyncMock(return_value=[])

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [
        DocumentResult(
            filename="thor_norse_mythology.txt",
            title="Thor in Norse Mythology",
            content="Thor's hammer is Mjolnir.",
            score=3.5,
        )
    ]

    mock_llm = MagicMock()
    mock_llm.is_configured.return_value = True
    mock_llm.provider_name = "Groq (llama-3.3-70b-versatile)"
    mock_llm.generate = AsyncMock(
        return_value="According to the text dataset, Thor wields Mjolnir, which returns automatically to his hand."
    )

    service = ChatbotService(
        settings=mock_settings,
        router=mock_router,
        dataset_retriever=mock_retriever,
        superhero_client=mock_superhero_client,
        llm_client=mock_llm,
    )

    request = AskRequest(question="What is Thor's hammer in Norse mythology?")
    response = await service.answer_question(request)

    assert response.route == "dataset"
    assert "Text Dataset (thor_norse_mythology.txt)" in response.sources
    assert "Mjolnir" in response.answer
    assert response.retrieved_documents == ["thor_norse_mythology.txt"]
    mock_superhero_client.search_character.assert_not_called()
    mock_retriever.search.assert_called_once()
