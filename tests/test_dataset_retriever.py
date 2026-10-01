"""Tests for TextDatasetRetriever using BM25 scoring."""

from pathlib import Path
import pytest
from app.services.dataset_retriever import TextDatasetRetriever

DATASET_DIR = Path(__file__).resolve().parent.parent / "data" / "mythology_and_legends"


@pytest.fixture
def retriever():
    return TextDatasetRetriever(DATASET_DIR)


def test_documents_indexed(retriever):
    assert retriever.doc_count > 0
    assert len(retriever.documents) >= 5


def test_retrieval_thor(retriever):
    results = retriever.search("Mjolnir hammer thunder lightning", top_k=2)
    assert len(results) > 0
    assert "thor" in results[0].filename.lower() or "thor" in results[0].title.lower()
    assert results[0].score > 0


def test_retrieval_hercules(retriever):
    results = retriever.search("Twelve Labours Nemean Lion Hydra Cerberus", top_k=2)
    assert len(results) > 0
    assert "hercules" in results[0].filename.lower()


def test_retrieval_anubis(retriever):
    results = retriever.search("mummification embalming weighing of the heart", top_k=2)
    assert len(results) > 0
    assert "anubis" in results[0].filename.lower()


def test_retrieval_empty_query(retriever):
    results = retriever.search("", top_k=2)
    assert results == []


def test_retrieval_unknown_query(retriever):
    results = retriever.search("xyzzyquantumsupercomputingalgorithm999", top_k=2)
    assert results == []
