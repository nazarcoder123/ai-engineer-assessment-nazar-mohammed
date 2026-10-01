"""Context Builder to format retrieved data from Superhero API and Text Dataset for the LLM."""

from typing import List, Tuple
from app.services.dataset_retriever import DocumentResult
from app.services.superhero_client import SuperheroData


class ContextBuilder:
    """Assembles retrieved evidence into prompt context and extracts source citations."""

    @staticmethod
    def build_context(
        route: str,
        superhero_results: List[SuperheroData],
        dataset_results: List[DocumentResult],
    ) -> Tuple[str, List[str]]:
        """
        Builds a structured context string and returns the list of source references.

        Returns:
            Tuple[str, List[str]]: (formatted_context_string, list_of_source_labels)
        """
        context_parts: List[str] = []
        sources: List[str] = []

        # 1. Format Superhero API Data
        if superhero_results:
            context_parts.append("=== SOURCE: SUPERHERO API ===")
            for hero in superhero_results:
                context_parts.append(hero.to_context_string())
                source_label = f"Superhero API ({hero.name})"
                if source_label not in sources:
                    sources.append(source_label)

        # 2. Format Text Dataset Data
        if dataset_results:
            context_parts.append("=== SOURCE: TEXT DATASET (MYTHOLOGY & LEGENDS) ===")
            for doc in dataset_results:
                context_parts.append(f"### Document: {doc.title} (File: {doc.filename})\n{doc.content}\n")
                source_label = f"Text Dataset ({doc.filename})"
                if source_label not in sources:
                    sources.append(source_label)

        # Fallback if no data was found
        if not context_parts:
            context_text = "No direct matching documents or superhero records were retrieved from the configured sources."
            sources.append("None (No matching records found)")
        else:
            context_text = "\n\n".join(context_parts)

        return context_text, sources

    @staticmethod
    def build_llm_prompt(question: str, context: str, route: str) -> str:
        """Constructs the prompt instructing the hosted LLM to answer with explicit citations."""
        return (
            "You are an AI chatbot assistant that answers questions accurately based on provided sources.\n"
            "You have access to information from two distinct knowledge domains:\n"
            "1. The Superhero API (comic book characters, powerstats, alter-egos, comic origins).\n"
            "2. A Curated Text Dataset of Ancient Mythology and Legends (Greek, Norse, Egyptian, Mesopotamian lore).\n\n"
            f"Active Route: {route.upper()}\n\n"
            "--- RETRIEVED CONTEXT START ---\n"
            f"{context}\n"
            "--- RETRIEVED CONTEXT END ---\n\n"
            f"USER QUESTION: {question}\n\n"
            "INSTRUCTIONS:\n"
            "- Answer the user's question directly, clearly, and concisely.\n"
            "- CRITICAL REQUIREMENT: Every response MUST explicitly state where each piece of information came from (e.g. 'According to the Superhero API...', 'Based on the Mythology Dataset...').\n"
            "- If the question involves both sources or a comparison (e.g. comparing Marvel Thor with Norse mythology Thor, or Superman vs Hercules), highlight similarities, differences, and distinct origins.\n"
            "- If the retrieved context does not contain sufficient details to answer, state honestly what is known and what could not be found.\n"
            "- Conclude with a brief 'Sources Consulted' section at the end of your answer."
        )
