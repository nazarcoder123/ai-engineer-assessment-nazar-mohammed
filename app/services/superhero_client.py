"""Superhero API Client for searching and retrieving superhero information."""

import logging
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SuperheroData(BaseModel):
    """Cleaned representation of a superhero profile for context injection."""
    id: str
    name: str
    full_name: str
    alter_egos: str
    aliases: List[str]
    publisher: str
    alignment: str
    first_appearance: str
    powerstats: Dict[str, str]
    gender: str
    race: str
    height: str
    weight: str
    work_occupation: str
    connections_group: str
    raw: Optional[Dict[str, Any]] = None

    def to_context_string(self) -> str:
        """Format the superhero details into a clean markdown block for LLM prompt."""
        stats_str = ", ".join([f"{k.capitalize()}: {v}" for k, v in self.powerstats.items()])
        aliases_str = ", ".join(self.aliases) if self.aliases else "None"
        
        return (
            f"### Superhero Profile: {self.name}\n"
            f"- **Real Name / Alter Ego**: {self.full_name or 'Unknown'} ({self.alter_egos})\n"
            f"- **Aliases**: {aliases_str}\n"
            f"- **Publisher**: {self.publisher}\n"
            f"- **Alignment**: {self.alignment}\n"
            f"- **Powerstats**: {stats_str}\n"
            f"- **Physical**: Gender: {self.gender}, Race: {self.race}, Height: {self.height}, Weight: {self.weight}\n"
            f"- **Occupation & Base**: {self.work_occupation}\n"
            f"- **Group Affiliations**: {self.connections_group}\n"
            f"- **First Appearance**: {self.first_appearance}\n"
        )


class SuperheroAPIClient:
    """Asynchronous client interacting with https://superheroapi.com."""

    def __init__(self, token: str, base_url: str = "https://superheroapi.com/api", timeout_seconds: float = 10.0):
        self.token = token.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    def is_configured(self) -> bool:
        """Returns True if a valid token format is present."""
        return bool(self.token and self.token != "your_superhero_api_token_here")

    async def search_character(self, name: str) -> List[SuperheroData]:
        """Search character by name via GET /api/{token}/search/{name}."""
        cleaned_name = name.strip()
        if not cleaned_name:
            return []

        if not self.is_configured():
            logger.warning("Superhero API token is not configured.")
            return []

        url = f"{self.base_url}/{self.token}/search/{cleaned_name}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            if data.get("response") != "success":
                logger.info(f"Superhero API search for '{cleaned_name}': {data.get('error', 'not found')}")
                return []

            results = data.get("results", [])
            characters: List[SuperheroData] = []

            for item in results:
                bio = item.get("biography", {})
                app = item.get("appearance", {})
                work = item.get("work", {})
                conn = item.get("connections", {})
                stats = item.get("powerstats", {})

                # Normalize height and weight
                height_list = app.get("height", [])
                height_str = " / ".join(height_list) if isinstance(height_list, list) else str(height_list)
                weight_list = app.get("weight", [])
                weight_str = " / ".join(weight_list) if isinstance(weight_list, list) else str(weight_list)

                aliases = bio.get("aliases", [])
                if isinstance(aliases, str):
                    aliases = [aliases]

                characters.append(
                    SuperheroData(
                        id=str(item.get("id", "")),
                        name=item.get("name", "Unknown"),
                        full_name=bio.get("full-name", ""),
                        alter_egos=bio.get("alter-egos", ""),
                        aliases=aliases,
                        publisher=bio.get("publisher", "Unknown"),
                        alignment=bio.get("alignment", "Unknown"),
                        first_appearance=bio.get("first-appearance", "Unknown"),
                        powerstats={k: str(v) for k, v in stats.items()},
                        gender=app.get("gender", "Unknown"),
                        race=app.get("race", "Unknown"),
                        height=height_str,
                        weight=weight_str,
                        work_occupation=work.get("occupation", "Unknown"),
                        connections_group=conn.get("group-affiliation", "Unknown"),
                    )
                )

            return characters

        except httpx.HTTPStatusError as e:
            logger.error(f"Superhero API returned HTTP error {e.response.status_code}: {e}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Network error while connecting to Superhero API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in Superhero API client: {e}")
            return []
