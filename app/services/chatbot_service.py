"""Chatbot Orchestrator service coordinating routing, retrieval, context building, and LLM synthesis."""

import logging
import time
from typing import List, Optional
from app.config import Settings
from app.models.request import AskRequest
from app.models.response import AskResponse
from app.services.context_builder import ContextBuilder
from app.services.dataset_retriever import DocumentResult, TextDatasetRetriever
from app.services.llm_client import BaseLLMClient, LLMAPIError, LLMConfigurationError, create_llm_client
from app.services.router import QuestionRouter, RoutingDecision
from app.services.superhero_client import SuperheroAPIClient, SuperheroData

logger = logging.getLogger(__name__)


class ChatbotService:
    """Core domain service executing the end-to-end question-answering workflow."""

    def __init__(
        self,
        settings: Settings,
        router: Optional[QuestionRouter] = None,
        dataset_retriever: Optional[TextDatasetRetriever] = None,
        superhero_client: Optional[SuperheroAPIClient] = None,
        llm_client: Optional[BaseLLMClient] = None,
    ):
        self.settings = settings
        self.router = router or QuestionRouter()
        self.dataset_retriever = dataset_retriever or TextDatasetRetriever(settings.absolute_dataset_path)
        self.superhero_client = superhero_client or SuperheroAPIClient(
            token=settings.superhero_api_token,
            base_url=settings.superhero_api_base_url,
        )
        self.llm_client = llm_client or create_llm_client(settings)

    async def answer_question(self, request: AskRequest) -> AskResponse:
        """Executes the pipeline: Validation -> Routing -> Retrieval -> Context -> LLM Generation."""
        start_time = time.perf_counter()
        question = request.question

        # Step 1: Routing
        # Use LLM-guided routing if available, else deterministic heuristics
        decision: RoutingDecision = await self.router.route_with_llm_or_fallback(
            question=question,
            llm_client=self.llm_client if self.llm_client.is_configured() else None,
        )

        route = decision.route
        superhero_results: List[SuperheroData] = []
        dataset_results: List[DocumentResult] = []

        # Step 2: Retrieve from Superhero API if route is 'superhero' or 'both'
        if route in ("superhero", "both"):
            hero_names = decision.superhero_names or [question]
            for name in hero_names[:2]:  # cap at top 2 to avoid latency spikes
                heroes = await self.superhero_client.search_character(name)
                for h in heroes:
                    if not any(existing.id == h.id for existing in superhero_results):
                        superhero_results.append(h)

        # Step 3: Retrieve from Text Dataset if route is 'dataset' or 'both'
        if route in ("dataset", "both"):
            dataset_query = decision.dataset_keywords or question
            dataset_results = self.dataset_retriever.search(dataset_query, top_k=2)

        # Step 4: Build Context and Source Citations
        context_str, sources = ContextBuilder.build_context(
            route=route,
            superhero_results=superhero_results,
            dataset_results=dataset_results,
        )

        # Check if Superhero API token was missing when superhero data was requested
        if route in ("superhero", "both") and not self.superhero_client.is_configured():
            sources.append("Superhero API (Warning: SUPERHERO_API_TOKEN not set in .env)")

        # Step 5: Call Hosted LLM Endpoint
        llm_provider_name = self.llm_client.provider_name
        if not self.llm_client.is_configured():
            # Graceful developer fallback when LLM API key has not yet been populated
            answer = (
                "⚠️ **Hosted LLM API Key is Not Configured**\n\n"
                f"The router successfully determined the route: **`{route.upper()}`**.\n\n"
                f"**Extracted Context & Evidence:**\n\n{context_str}\n\n"
                "> **Next Step:** To enable live synthesis from a hosted LLM, please set `GROQ_API_KEY` (free at console.groq.com) "
                "or `GEMINI_API_KEY` (free at aistudio.google.com) in your `.env` file."
            )
            llm_provider_name = "Not Configured (Preview Mode)"
        else:
            prompt = ContextBuilder.build_llm_prompt(question=question, context=context_str, route=route)
            try:
                answer = await self.llm_client.generate(prompt)
            except LLMAPIError as e:
                logger.error(f"LLM API generation failed: {e}")
                answer = (
                    f"⚠️ An error occurred while communicating with the hosted LLM endpoint ({llm_provider_name}):\n"
                    f"{str(e)}\n\n"
                    f"**Retrieved Context was:**\n{context_str}"
                )
            except Exception as e:
                logger.error(f"Unexpected error calling LLM: {e}")
                answer = f"⚠️ Unexpected error during LLM generation: {str(e)}"

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return AskResponse(
            answer=answer,
            sources=sources,
            route=route,
            retrieved_superheroes=[h.name for h in superhero_results] if superhero_results else None,
            retrieved_documents=[d.filename for d in dataset_results] if dataset_results else None,
            latency_ms=elapsed_ms,
            llm_provider=llm_provider_name,
        )
