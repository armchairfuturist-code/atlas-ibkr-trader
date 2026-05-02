"""Reflection system for learning from trade outcomes.

Inspired by TradingAgents' reflection mechanism - after trade execution,
analyzes the outcome and stores lessons for future reference.
"""

import logging
from datetime import datetime
from typing import Optional

from app.memory.financial_memory import FinancialSituationMemory, MemoryEntry

logger = logging.getLogger(__name__)

# Global memory instance (can be replaced with dependency injection)
_memory_instance: Optional[FinancialSituationMemory] = None


def get_memory() -> FinancialSituationMemory:
    """Get or create the global memory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = FinancialSituationMemory()
    return _memory_instance


def set_memory(memory: FinancialSituationMemory) -> None:
    """Set the global memory instance (for testing)."""
    global _memory_instance
    _memory_instance = memory


def reflect_and_remember(trade_result: dict) -> Optional[MemoryEntry]:
    """Store trade outcome in memory for future reference.

    Call this after a trade is closed/executed to learn from the outcome.

    Args:
        trade_result: Dict with keys:
            - ticker: Stock symbol
            - direction: "LONG" or "SHORT"
            - rating: SignalRating value
            - conviction: Conviction level (1-100)
            - macro_regime: "RISK_ON", "RISK_OFF", or "NEUTRAL"
            - sector: Sector name
            - pnl_pct: Profit/loss percentage
            - holding_days: Days the position was held
            - entry_price: Entry price
            - exit_price: Exit price

    Returns:
        The created MemoryEntry, or None on failure
    """
    try:
        memory = get_memory()

        # Build situation description
        situation_parts = [
            f"Ticker: {trade_result.get('ticker', 'UNKNOWN')}",
            f"Direction: {trade_result.get('direction', 'NEUTRAL')}",
            f"Rating: {trade_result.get('rating', 'HOLD')}",
            f"Conviction: {trade_result.get('conviction', 50)}",
            f"Regime: {trade_result.get('macro_regime', 'NEUTRAL')}",
            f"Sector: {trade_result.get('sector', 'unknown')}",
        ]
        situation = ", ".join(situation_parts)

        # Build outcome description
        pnl = trade_result.get("pnl_pct", 0)
        holding_days = trade_result.get("holding_days", 0)
        entry = trade_result.get("entry_price", 0)
        exit = trade_result.get("exit_price", 0)

        outcome_parts = [
            f"PnL: {pnl:+.2f}%",
            f"Holding period: {holding_days} days",
        ]
        if entry and exit:
            outcome_parts.append(f"Entry: ${entry:.2f}, Exit: ${exit:.2f}")
        outcome = ", ".join(outcome_parts)

        # Derive lesson
        lesson = _derive_lesson(trade_result)

        # Build tags
        tags = [
            trade_result.get("direction", "neutral").lower(),
            trade_result.get("rating", "HOLD").lower(),
            _regime_to_tag(trade_result.get("macro_regime", "NEUTRAL")),
        ]

        # Add outcome-based tags
        if pnl > 3:
            tags.append("profitable")
        elif pnl < -2:
            tags.append("loss")

        memory.add_memory(
            situation=situation, outcome=outcome, lesson=lesson, tags=tags
        )

        logger.info(
            f"Stored trade memory: {trade_result.get('ticker')} "
            f"{trade_result.get('direction')} {pnl:+.2f}% - {lesson[:50]}"
        )

        return MemoryEntry(
            situation=situation, outcome=outcome, lesson=lesson, tags=tags
        )

    except Exception as e:
        logger.error(f"Failed to reflect on trade result: {e}")
        return None


def _derive_lesson(trade_result: dict) -> str:
    """Derive a lesson from the trade result.

    Uses simple heuristics to generate a lesson.
    In production, could use LLM analysis.
    """
    pnl = trade_result.get("pnl_pct", 0)
    conviction = trade_result.get("conviction", 50)
    rating = trade_result.get("rating", "HOLD")
    holding_days = trade_result.get("holding_days", 0)

    lessons = []

    # PnL-based lessons
    if pnl > 5:
        lessons.append(f"High conviction {rating} trades can deliver strong returns")
    elif pnl > 2:
        lessons.append(f"Profitable trade - thesis confirmed")
    elif pnl < -3:
        lessons.append("Stop loss discipline needed - large drawdown")
    elif pnl < 0:
        lessons.append("Thesis did not pan out - review signals")

    # Holding period lessons
    if holding_days <= 2 and abs(pnl) > 1:
        lessons.append("Quick move - consider tighter stops next time")
    elif holding_days > 20 and abs(pnl) < 1:
        lessons.append("Position moved slowly - set time-based exits")

    # Conviction lessons
    if conviction >= 80 and pnl < 0:
        lessons.append("High conviction does not guarantee success - respect stops")
    elif conviction < 40 and abs(pnl) > 3:
        lessons.append("Low conviction positions can still work - thesis was wrong")

    return lessons[0] if lessons else "No significant lesson - trade as expected"


def _regime_to_tag(regime: str) -> str:
    """Convert regime to tag."""
    mapping = {
        "RISK_ON": "risk-on",
        "RISK_OFF": "risk-off",
        "NEUTRAL": "neutral-regime",
    }
    return mapping.get(regime, "unknown-regime")
