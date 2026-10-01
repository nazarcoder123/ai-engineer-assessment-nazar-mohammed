"""Tests for QuestionRouter determining source categories: dataset, superhero, or both."""

import pytest
from app.services.router import QuestionRouter


@pytest.fixture
def router():
    return QuestionRouter()


def test_route_superhero_only(router):
    decision1 = router.route_heuristically("What are Batman's powerstats and alter ego?")
    assert decision1.route == "superhero"
    assert "batman" in decision1.superhero_names

    decision2 = router.route_heuristically("Who is Peter Parker in Spider-Man comics?")
    assert decision2.route == "superhero"


def test_route_dataset_only(router):
    decision1 = router.route_heuristically("What were the Twelve Labours of Heracles in Greek mythology?")
    assert decision1.route == "dataset"

    decision2 = router.route_heuristically("Who is Anubis and what is the Egyptian Weighing of the Heart?")
    assert decision2.route == "dataset"

    decision3 = router.route_heuristically("Tell me about the Epic of Gilgamesh and Enkidu.")
    assert decision3.route == "dataset"


def test_route_both_sources_comparison(router):
    decision1 = router.route_heuristically("Compare Superman to Hercules in terms of physical strength.")
    assert decision1.route == "both"
    assert "superman" in decision1.superhero_names or "hercules" in decision1.superhero_names

    decision2 = router.route_heuristically("Compare Marvel's Thor with the mythological Norse Thor.")
    assert decision2.route == "both"


def test_route_overlapping_entity(router):
    # Thor is an overlapping entity in both myth and comics
    decision = router.route_heuristically("Tell me about Thor")
    assert decision.route in ("both", "dataset", "superhero")
    assert "thor" in decision.superhero_names or "thor" in decision.dataset_keywords.lower()


def test_route_fallback(router):
    # Completely generic question defaults safely to 'both'
    decision = router.route_heuristically("Who is the most powerful warrior?")
    assert decision.route == "both"
