"""Re-export production BM25 so eval/bakeoff cannot drift from the live path."""

from backend.services.rag_bm25 import BM25, Scored, tokenize

__all__ = ["BM25", "Scored", "tokenize"]
