"""Text dataset retrieval engine using BM25 ranking."""

import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel


class Document(BaseModel):
    """Represents a text document loaded from the dataset."""
    filename: str
    title: str
    category: str
    keywords: List[str]
    content: str
    token_count: int


class DocumentResult(BaseModel):
    """Result of a dataset search."""
    filename: str
    title: str
    content: str
    score: float


class TextDatasetRetriever:
    """In-memory BM25 retrieval engine for text files in the dataset directory."""

    def __init__(self, dataset_dir: Path, k1: float = 1.5, b: float = 0.75):
        self.dataset_dir = Path(dataset_dir)
        self.k1 = k1
        self.b = b
        self.documents: List[Document] = []
        self.doc_term_freqs: List[Dict[str, int]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_count: int = 0
        self.idf: Dict[str, float] = {}
        self._load_documents()

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple tokenizer that extracts lowercase alphanumeric tokens."""
        return re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())

    def _load_documents(self) -> None:
        """Loads and indexes all .txt files from the dataset directory."""
        if not self.dataset_dir.exists():
            return

        txt_files = sorted(list(self.dataset_dir.glob("*.txt")))
        temp_docs = []
        temp_tfs = []
        temp_lengths = []
        term_doc_occurrences: Dict[str, int] = {}

        for file_path in txt_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception:
                continue

            # Extract title, category, keywords if header format is present
            title = file_path.stem.replace("_", " ").title()
            category = "General"
            keywords = []
            
            lines = content.splitlines()
            for line in lines[:5]:
                if line.lower().startswith("title:"):
                    title = line.split(":", 1)[1].strip()
                elif line.lower().startswith("category:"):
                    category = line.split(":", 1)[1].strip()
                elif line.lower().startswith("keywords:"):
                    keywords = [k.strip() for k in line.split(":", 1)[1].split(",")]

            tokens = self.tokenize(content)
            doc_len = len(tokens)
            if doc_len == 0:
                continue

            tf: Dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1

            for token in tf.keys():
                term_doc_occurrences[token] = term_doc_occurrences.get(token, 0) + 1

            doc = Document(
                filename=file_path.name,
                title=title,
                category=category,
                keywords=keywords,
                content=content,
                token_count=doc_len,
            )
            temp_docs.append(doc)
            temp_tfs.append(tf)
            temp_lengths.append(doc_len)

        self.documents = temp_docs
        self.doc_term_freqs = temp_tfs
        self.doc_lengths = temp_lengths
        self.doc_count = len(temp_docs)

        if self.doc_count > 0:
            self.avg_doc_len = sum(self.doc_lengths) / self.doc_count

            # Calculate BM25 Robertson-Sparck Jones IDF
            for term, doc_freq in term_doc_occurrences.items():
                self.idf[term] = math.log(
                    (self.doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0
                )

    def search(self, query: str, top_k: int = 2, min_score: float = 0.1) -> List[DocumentResult]:
        """Search the indexed dataset for documents relevant to the query using BM25."""
        if not self.documents:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores: List[float] = [0.0] * self.doc_count

        for q_token in query_tokens:
            if q_token not in self.idf:
                continue
            token_idf = self.idf[q_token]

            for idx in range(self.doc_count):
                tf = self.doc_term_freqs[idx].get(q_token, 0)
                if tf == 0:
                    continue
                doc_len = self.doc_lengths[idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                scores[idx] += token_idf * (numerator / denominator)

        # Pair results with index and sort descending
        scored_docs: List[Tuple[float, int]] = [
            (scores[i], i) for i in range(self.doc_count) if scores[i] >= min_score
        ]
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results: List[DocumentResult] = []
        for score, idx in scored_docs[:top_k]:
            doc = self.documents[idx]
            results.append(
                DocumentResult(
                    filename=doc.filename,
                    title=doc.title,
                    content=doc.content,
                    score=round(score, 4),
                )
            )

        return results
