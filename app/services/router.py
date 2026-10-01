"""Question Router that determines the relevant source: 'dataset', 'superhero', or 'both'."""

import json
import logging
import re
from typing import Any, List, Literal, Optional, Tuple
from pydantic import BaseModel

logger = logging.getLogger(__name__)

RouteType = Literal["dataset", "superhero", "both"]


class RoutingDecision(BaseModel):
    """Result of question routing."""
    route: RouteType
    superhero_names: List[str] = []
    dataset_keywords: str = ""
    reasoning: str = ""


class QuestionRouter:
    """Routes incoming natural-language questions to the appropriate knowledge source."""

    # Common superhero terms and comic entities
    SUPERHERO_SIGNALS = {
        "superman", "batman", "spiderman", "spider-man", "iron man", "ironman", "captain america",
        "thor", "hulk", "black widow", "hawkeye", "wolverine", "deadpool", "flash", "wonder woman",
        "aquaman", "cyborg", "green lantern", "shazam", "black panther", "doctor strange",
        "thanos", "joker", "magneto", "superhero", "superheroes", "supervillain", "villain",
        "avengers", "justice league", "x-men", "marvel", "dc", "comic", "comics", "mutant",
        "kryptonite", "gotham", "metropolis", "stark", "wayne", "peter parker", "clark kent",
        "bruce wayne", "powerstats", "alter ego"
    }

    # Text dataset signals (Mythology & Legends)
    DATASET_SIGNALS = {
        "mythology", "myth", "myths", "legend", "legends", "pantheon", "god", "goddess", "deity",
        "zeus", "odin", "hercules", "heracles", "ares", "athena", "loki", "gilgamesh", "achilles",
        "anubis", "olympus", "mount olympus", "asgard", "midgard", "valhalla", "yggdrasil",
        "ragnarok", "mjolnir", "twelve labours", "trojan war", "uruk", "enkidu", "nemean lion",
        "hydra", "cerberus", "mummification", "embalming", "river styx", "norse", "greek",
        "egyptian", "mesopotamian", "ancient", "titan", "titanomachy", "kronos"
    }

    # Entities that exist in BOTH domains (e.g., mythological figures adapted into comic superheroes)
    OVERLAPPING_ENTITIES = {"thor", "hercules", "loki", "ares", "zeus", "gilgamesh", "odin", "athena"}

    # Comparison terms indicating a cross-source question
    COMPARISON_SIGNALS = {
        "compare", "difference", "versus", "vs", "against", "stronger", "faster", "more powerful",
        "both", "relationship between", "how does", "contrast", "in comparison to"
    }

    def route_heuristically(self, question: str) -> RoutingDecision:
        """Deterministic keyword-based routing heuristic with entity extraction."""
        lower_q = question.lower()
        words = set(re.findall(r"\b[a-zA-Z0-9_-]+\b", lower_q))

        # Check multi-word phrase matches
        has_superhero_phrase = any(phrase in lower_q for phrase in self.SUPERHERO_SIGNALS)
        has_dataset_phrase = any(phrase in lower_q for phrase in self.DATASET_SIGNALS)

        superhero_matches = [w for w in self.SUPERHERO_SIGNALS if w in lower_q or w in words]
        dataset_matches = [w for w in self.DATASET_SIGNALS if w in lower_q or w in words]
        is_comparison = any(comp in lower_q for comp in self.COMPARISON_SIGNALS)

        # Check for overlapping entities (e.g. Thor)
        overlap_found = [e for e in self.OVERLAPPING_ENTITIES if e in lower_q or e in words]

        # Extract potential superhero names for the API search
        extracted_heroes: List[str] = []
        for hero in [
            "batman", "superman", "spider-man", "iron man", "hulk", "thor", "wolverine",
            "flash", "wonder woman", "aquaman", "loki", "hercules", "ares", "gilgamesh",
            "captain america", "deadpool", "black panther", "doctor strange", "thanos", "joker"
        ]:
            if hero in lower_q:
                extracted_heroes.append(hero)

        # Default fallback extraction: if no known hero was matched, check if question says "who is X"
        if not extracted_heroes:
            m = re.search(r"\b(?:who is|about|powers of|stats for)\s+([a-zA-Z\s]{3,20})", lower_q)
            if m:
                candidate = m.group(1).strip()
                if candidate not in {"a", "an", "the", "in", "of"}:
                    extracted_heroes.append(candidate)

        comic_specific = {
            "comic", "comics", "marvel", "dc", "mcu", "avengers", "justice league",
            "superhero", "superheroes", "supervillain", "powerstats", "alter ego",
            "stark", "wayne", "peter parker", "clark kent", "bruce wayne", "krypton", "gotham"
        }
        dataset_specific = {
            "mythology", "myth", "myths", "legend", "legends", "pantheon", "god", "goddess", "deity",
            "norse", "greek", "egyptian", "mesopotamian", "ancient", "titan", "epic", "edda",
            "iliad", "odyssey", "trojan war", "twelve labours", "weighing of the heart", "enuma elish",
            "olympus", "asgard", "valhalla", "yggdrasil", "ragnarok", "styx", "underworld", "enkidu", "uruk"
        }

        has_comic = any(c in lower_q for c in comic_specific)
        has_dataset = any(d in lower_q for d in dataset_specific)

        # Decision Logic:
        # Case 1: Overlapping entity (e.g. Thor, Hercules, Gilgamesh)
        if overlap_found:
            # Explicit comparison between comic and myth versions
            if is_comparison or (has_comic and has_dataset):
                return RoutingDecision(
                    route="both",
                    superhero_names=extracted_heroes or overlap_found,
                    dataset_keywords=question,
                    reasoning=f"Question compares overlapping entity '{', '.join(overlap_found)}' across myth and superhero lore.",
                )
            # Question explicitly mentions comic / superhero specific terms
            if has_comic and not has_dataset:
                return RoutingDecision(
                    route="superhero",
                    superhero_names=extracted_heroes or overlap_found,
                    dataset_keywords="",
                    reasoning=f"Question specifically focuses on the comic/superhero incarnation of {', '.join(overlap_found)}.",
                )
            # Question explicitly mentions mythology / dataset specific terms
            if has_dataset and not has_comic:
                return RoutingDecision(
                    route="dataset",
                    superhero_names=[],
                    dataset_keywords=question,
                    reasoning=f"Question targets the mythological lore of {', '.join(overlap_found)}.",
                )
            # Ambiguous single-entity mention: route to both to provide rich dual context
            return RoutingDecision(
                route="both",
                superhero_names=extracted_heroes or overlap_found,
                dataset_keywords=question,
                reasoning=f"Entity '{', '.join(overlap_found)}' exists in both the text dataset and superhero lore; querying both.",
            )

        # Case 2: Comparison between two distinct entities (e.g. Superman vs Hercules)
        if (has_superhero_phrase or superhero_matches) and (has_dataset_phrase or dataset_matches):
            return RoutingDecision(
                route="both",
                superhero_names=extracted_heroes,
                dataset_keywords=question,
                reasoning="Question references elements from both superhero lore and the mythology dataset.",
            )

        # Case 3: Strictly Superhero
        if has_superhero_phrase or superhero_matches:
            return RoutingDecision(
                route="superhero",
                superhero_names=extracted_heroes,
                dataset_keywords="",
                reasoning="Question is about superheroes or comic book entities.",
            )

        # Case 4: Strictly Dataset
        if has_dataset_phrase or dataset_matches:
            return RoutingDecision(
                route="dataset",
                superhero_names=[],
                dataset_keywords=question,
                reasoning="Question is about ancient mythology, deities, or legendary heroes in the text dataset.",
            )

        # Default fallback when query is generic (e.g. "Who has more physical strength?")
        return RoutingDecision(
            route="both",
            superhero_names=extracted_heroes,
            dataset_keywords=question,
            reasoning="Uncertain domain boundary; querying both sources to maximize context relevance.",
        )

    async def route_with_llm_or_fallback(self, question: str, llm_client: Optional[Any] = None) -> RoutingDecision:
        """Route using LLM classification if available, otherwise use deterministic heuristic."""
        if not llm_client or not getattr(llm_client, "is_configured", lambda: False)():
            return self.route_heuristically(question)

        prompt = (
            "You are a router for a chatbot that answers questions using two sources:\n"
            "Source A: 'superhero' -> Superhero API (for comic book superheroes like Batman, Superman, Spider-Man, Avengers).\n"
            "Source B: 'dataset' -> Text Dataset on Ancient Mythology & Legends (Thor in Norse myth, Hercules 12 labours, Zeus, Odin, Ares, Loki, Gilgamesh, Achilles, Athena, Anubis).\n"
            "Source C: 'both' -> When the question compares both, or involves entities in both (e.g. comparing Marvel Thor with Norse Thor, or Superman vs Hercules).\n\n"
            f"User Question: \"{question}\"\n\n"
            "Respond ONLY with a JSON object in this exact schema without any code blocks or explanation:\n"
            "{\n"
            '  "route": "dataset" | "superhero" | "both",\n'
            '  "superhero_names": ["list", "of", "names"],\n'
            '  "dataset_keywords": "search query for mythology dataset",\n'
            '  "reasoning": "brief 1-sentence reason"\n'
            "}"
        )

        try:
            raw_response = await llm_client.generate(prompt, temperature=0.0)
            cleaned = raw_response.strip()
            # Strip markdown code fencing if present
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
                cleaned = re.sub(r"\n?```$", "", cleaned)
            data = json.loads(cleaned)

            route_val = data.get("route", "both").lower()
            if route_val not in ("dataset", "superhero", "both"):
                route_val = "both"

            return RoutingDecision(
                route=route_val,
                superhero_names=data.get("superhero_names", []),
                dataset_keywords=data.get("dataset_keywords", question),
                reasoning=data.get("reasoning", "LLM-guided classification."),
            )
        except Exception as e:
            logger.warning(f"LLM routing failed ({e}), falling back to deterministic heuristic.")
            return self.route_heuristically(question)
