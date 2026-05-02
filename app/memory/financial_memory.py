"""BM25-based memory for financial situations.

Inspired by TradingAgents' FinancialSituationMemory - stores past trading
situations and retrieves similar ones for experiential learning.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import to handle missing dependency gracefully
BM25Okapi = None
try:
    from rank_bm25 import BM25Okapi
except ImportError:
    logger.warning("rank-bm25 not installed. BM25 features will be limited.")


@dataclass
class MemoryEntry:
    """A stored memory of a past trading situation."""

    situation: str  # Descriptive text of the situation
    outcome: str  # Outcome (PnL, what happened)
    lesson: str  # Lesson learned
    timestamp: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(
        default_factory=list
    )  # e.g., ["bull", "high-conv", "earnings"]


class FinancialSituationMemory:
    """BM25-based memory for past trading situations.

    Uses BM25 (Okapi BM25) for text retrieval - no embeddings,
    no API calls, fully offline and stateless.

    Example:
        memory = FinancialSituationMemory()
        memory.add_memory(
            situation="Ticker SPY, RISK_ON regime, BUY rating, conviction 85",
            outcome="PnL +2.5%, held for 5 days",
            lesson="High conviction RISK_ON setups work well for SPY"
        )

        similar = memory.get_memories(
            "Ticker SPY, RISK_ON regime, conviction 80",
            n=3
        )
    """

    def __init__(self):
        self.entries: list[MemoryEntry] = []
        self.bm25: Optional["BM25Okapi"] = None
        self._tokenized_corpus: list[list[str]] = []

    def add_memory(
        self, situation: str, outcome: str, lesson: str, tags: list[str] = None
    ) -> None:
        """Store a new trading situation and its outcome.

        Args:
            situation: Description of the trading situation
            outcome: What happened (PnL, holding period, etc.)
            lesson: Key takeaway or lesson learned
            tags: Optional tags for categorization
        """
        entry = MemoryEntry(
            situation=situation,
            outcome=outcome,
            lesson=lesson,
            timestamp=datetime.now(),
            tags=tags or [],
        )

        self.entries.append(entry)
        self._rebuild_index()

        logger.debug(f"Added memory: {situation[:50]}... (total: {len(self.entries)})")

    def get_memories(self, current_situation: str, n: int = 3) -> list[MemoryEntry]:
        """Retrieve similar past situations to the current one.

        Args:
            current_situation: Description of current trading situation
            n: Number of similar situations to return

        Returns:
            List of most similar MemoryEntries (max n)
        """
        if not self.entries or self.bm25 is None:
            logger.debug("No memories stored yet")
            return []

        if BM25Okapi is None:
            # Fallback: return most recent entries
            return self.entries[-n:]

        # Tokenize query
        query_tokens = self._tokenize(current_situation)

        if not query_tokens:
            return self.entries[-n:]

        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)

        # Get top N indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[
            :n
        ]

        # Return entries with non-zero scores
        result = []
        for idx in top_indices:
            if scores[idx] > 0:
                result.append(self.entries[idx])

        logger.debug(
            f"Retrieved {len(result)} similar memories for: {current_situation[:50]}"
        )

        return result

    def get_recent_memories(self, n: int = 10) -> list[MemoryEntry]:
        """Get the N most recent memories (ignores relevance).

        Useful for reviewing recent experience.
        """
        return self.entries[-n:] if self.entries else []

    def search_by_tag(self, tag: str) -> list[MemoryEntry]:
        """Search memories by tag."""
        return [e for e in self.entries if tag in e.tags]

    def get_statistics(self) -> dict:
        """Get memory statistics."""
        return {
            "total_memories": len(self.entries),
            "oldest": self.entries[0].timestamp.isoformat() if self.entries else None,
            "newest": self.entries[-1].timestamp.isoformat() if self.entries else None,
            "has_bm25_index": self.bm25 is not None,
        }

    def clear(self) -> None:
        """Clear all memories (use with caution)."""
        self.entries = []
        self._tokenized_corpus = []
        self.bm25 = None
        logger.info("Memory cleared")

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization - lowercase, split on non-alphanumeric."""
        if not text:
            return []
        text = text.lower()
        tokens = re.findall(r"\w+", text)
        # Filter very short tokens
        return [t for t in tokens if len(t) > 2]

    def _rebuild_index(self) -> None:
        """Rebuild BM25 index from all entries."""
        if BM25Okapi is None:
            self.bm25 = None
            return

        if not self.entries:
            self.bm25 = None
            self._tokenized_corpus = []
            return

        # Tokenize all situations
        self._tokenized_corpus = [
            self._tokenize(entry.situation) for entry in self.entries
        ]

        # Build BM25 index
        self.bm25 = BM25Okapi(self._tokenized_corpus)

        logger.debug(f"Rebuilt BM25 index with {len(self.entries)} entries")

    def __len__(self) -> int:
        """Return number of stored memories."""
        return len(self.entries)
