"""Tests for ContextBuilder assembling prompt context and source citations."""

from app.services.context_builder import ContextBuilder
from app.services.dataset_retriever import DocumentResult
from app.services.superhero_client import SuperheroData


def test_build_context_superhero_only():
    hero = SuperheroData(
        id="1",
        name="Flash",
        full_name="Barry Allen",
        alter_egos="No",
        aliases=["Scarlet Speedster"],
        publisher="DC Comics",
        alignment="good",
        first_appearance="Showcase #4",
        powerstats={"speed": "100", "intelligence": "88"},
        gender="Male",
        race="Human",
        height="6'0",
        weight="195 lb",
        work_occupation="Forensic Scientist",
        connections_group="Justice League",
    )

    context_str, sources = ContextBuilder.build_context(
        route="superhero",
        superhero_results=[hero],
        dataset_results=[],
    )

    assert "SOURCE: SUPERHERO API" in context_str
    assert "Barry Allen" in context_str
    assert "Speed: 100" in context_str
    assert sources == ["Superhero API (Flash)"]


def test_build_context_dataset_only():
    doc = DocumentResult(
        filename="thor_norse_mythology.txt",
        title="Thor in Norse Mythology",
        content="Thor wields Mjolnir forged by dwarven smiths.",
        score=2.45,
    )

    context_str, sources = ContextBuilder.build_context(
        route="dataset",
        superhero_results=[],
        dataset_results=[doc],
    )

    assert "SOURCE: TEXT DATASET" in context_str
    assert "Mjolnir" in context_str
    assert sources == ["Text Dataset (thor_norse_mythology.txt)"]


def test_build_context_both_sources():
    hero = SuperheroData(
        id="70",
        name="Batman",
        full_name="Bruce Wayne",
        alter_egos="None",
        aliases=[],
        publisher="DC Comics",
        alignment="good",
        first_appearance="Detective Comics #27",
        powerstats={"combat": "100"},
        gender="Male",
        race="Human",
        height="6'2",
        weight="210 lb",
        work_occupation="CEO",
        connections_group="Justice League",
    )
    doc = DocumentResult(
        filename="achilles_trojan_war.txt",
        title="Achilles and the Trojan War",
        content="Achilles was dipped in the River Styx.",
        score=1.85,
    )

    context_str, sources = ContextBuilder.build_context(
        route="both",
        superhero_results=[hero],
        dataset_results=[doc],
    )

    assert "SOURCE: SUPERHERO API" in context_str
    assert "SOURCE: TEXT DATASET" in context_str
    assert "Superhero API (Batman)" in sources
    assert "Text Dataset (achilles_trojan_war.txt)" in sources


def test_build_llm_prompt():
    prompt = ContextBuilder.build_llm_prompt(
        question="Compare Thor to Odin",
        context="Mock context info",
        route="both",
    )
    assert "USER QUESTION: Compare Thor to Odin" in prompt
    assert "Every response MUST explicitly state where each piece of information came from" in prompt
    assert "Mock context info" in prompt
