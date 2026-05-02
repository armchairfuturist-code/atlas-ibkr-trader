"""Autopredict adapter for Polymarket execution.

Bridges the macro-thematic analysis system to autopredict's execution framework.

autopredict requires:
- fair_prob: Our probability forecast for the market
- market_prob: Current market price (from Polymarket)
- It then evaluates: edge, spread, liquidity, time to expiry

This adapter:
1. Converts our thematic analysis to fair_prob estimates
2. Matches forecasts to relevant Polymarket markets
3. Provides execution parameters based on autopredict logic
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any, Optional
from enum import Enum

from app.data.polymarket_client import PolymarketClient, PolymarketMarket
from app.layers.macro_thematic import MacroThematicLayer, ThematicDirection


logger = logging.getLogger(__name__)


class TradeDecision(Enum):
    """autpredict trade decision."""

    BUY_YES = "BUY_YES"  # Buy YES tokens (long the event)
    BUY_NO = "BUY_NO"  # Buy NO tokens (short the event)
    SKIP = "SKIP"  # Don't trade (insufficient edge/spread)
    WAIT = "WAIT"  # Wait for better conditions


@dataclass
class FairProbabilityEstimate:
    """Our probability estimate for a Polymarket event."""

    market_id: str
    question: str
    fair_prob: float  # Our estimate (0-1)
    market_prob: float  # Current market price (0-1)
    edge: float  # fair_prob - market_prob
    confidence: int  # 1-100
    thesis: str
    source: str  # "geopolitical", "technical", "macro"


@dataclass
class AutopredictExecution:
    """Execution parameters from autopredict logic."""

    decision: TradeDecision
    market_id: str
    size_usd: float
    order_type: str  # "market" or "limit"
    limit_price: Optional[float]
    rationale: str
    edge: float
    spread_pct: float
    estimated_fill_rate: float
    risk_reward_ratio: float


class AutopredictAdapter:
    """Bridges thematic analysis to autopredict execution.

    Based on autopredict's agent logic:
    - Evaluates edge (fair_prob - market_prob)
    - Checks spread width
    - Estimates fill rate
    - Decides order type (market vs limit)
    - Calculates position size based on edge and bankroll
    """

    def __init__(
        self,
        min_edge: float = 0.05,  # Minimum edge to trade (5%)
        min_liq_depth: float = 1000.0,  # Minimum liquidity depth ($)
        max_spread_pct: float = 0.03,  # Maximum spread (3%)
        bankroll_fraction: float = 0.02,  # Max 2% of bankroll per trade
        aggressive_edge_mult: float = 3.0,  # Edge/spread ratio for market orders
    ):
        """Initialize with autopredict-style parameters."""
        self.min_edge = min_edge
        self.min_liq_depth = min_liq_depth
        self.max_spread_pct = max_spread_pct
        self.bankroll_fraction = bankroll_fraction
        self.aggressive_edge_mult = aggressive_edge_mult
        self.polymarket = PolymarketClient()

    def generate_fair_prob_estimates(
        self,
        theme: Optional[str] = None,
    ) -> list[FairProbabilityEstimate]:
        """Generate fair probability estimates from thematic analysis.

        This is the key bridge between our system and autopredict.
        autopredict needs fair_prob as input - we derive it from:
        1. Polymarket market data
        2. Our geopolitical/technical analysis
        3. Event-specific probability modeling

        Args:
            theme: Optional theme to focus on (e.g., "iran", "oil")

        Returns:
            List of FairProbabilityEstimate objects
        """
        estimates = []

        try:
            markets = self.polymarket.get_geopolitical_markets()
        except Exception as e:
            logger.warning(f"Failed to get Polymarket data: {e}")
            return estimates

        for market in markets[:20]:  # Process top 20 markets
            market_id = market.get("market_id", "")
            question = market.get("question", "")
            market_prob = market.get("yes_probability", 0.5)
            volume_24h = market.get("volume_24h", 0)

            # Derive fair_prob from event type
            fair_prob, confidence, thesis = self._estimate_fair_prob(
                question, market_prob, theme
            )

            if fair_prob is not None:
                edge = fair_prob - market_prob
                estimates.append(
                    FairProbabilityEstimate(
                        market_id=market_id,
                        question=question,
                        fair_prob=fair_prob,
                        market_prob=market_prob,
                        edge=edge,
                        confidence=confidence,
                        thesis=thesis,
                        source="geopolitical",
                    )
                )

        return estimates

    def evaluate_trade(
        self,
        estimate: FairProbabilityEstimate,
        liquidity_depth: float = 5000.0,
        spread_pct: float = 0.02,
        time_to_expiry_hours: float = 168.0,  # Default 1 week
        bankroll: float = 10000.0,  # Default bankroll
    ) -> AutopredictExecution:
        """Evaluate whether to trade using autopredict logic.

        Based on autopredict's agent.py decision flow:
        1. Gating checks (edge, liquidity, spread)
        2. Order type decision (market vs limit)
        3. Position sizing

        Args:
            estimate: Fair probability estimate
            liquidity_depth: Available liquidity in $
            spread_pct: Spread as percentage
            time_to_expiry_hours: Hours until market expiry
            bankroll: Trading bankroll in $

        Returns:
            AutopredictExecution with decision and parameters
        """
        fair_prob = estimate.fair_prob
        market_prob = estimate.market_prob
        edge = estimate.edge

        # Gating checks
        if abs(edge) < self.min_edge:
            return AutopredictExecution(
                decision=TradeDecision.SKIP,
                market_id=estimate.market_id,
                size_usd=0.0,
                order_type="none",
                limit_price=None,
                rationale=f"Edge {edge:.1%} below minimum {self.min_edge:.1%}",
                edge=edge,
                spread_pct=spread_pct,
                estimated_fill_rate=0.0,
                risk_reward_ratio=0.0,
            )

        if liquidity_depth < self.min_liq_depth:
            return AutopredictExecution(
                decision=TradeDecision.SKIP,
                market_id=estimate.market_id,
                size_usd=0.0,
                order_type="none",
                limit_price=None,
                rationale=f"Liquidity ${liquidity_depth:.0f} below minimum${self.min_liq_depth:.0f}",
                edge=edge,
                spread_pct=spread_pct,
                estimated_fill_rate=0.0,
                risk_reward_ratio=0.0,
            )

        if spread_pct > self.max_spread_pct:
            return AutopredictExecution(
                decision=TradeDecision.WAIT,
                market_id=estimate.market_id,
                size_usd=0.0,
                order_type="none",
                limit_price=None,
                rationale=f"Spread{spread_pct:.1%} too wide (max {self.max_spread_pct:.1%})",
                edge=edge,
                spread_pct=spread_pct,
                estimated_fill_rate=0.0,
                risk_reward_ratio=0.0,
            )

        # Determine direction
        if edge > 0:
            # Our estimate higher than market - buy YES
            decision = TradeDecision.BUY_YES
            target_price = min(fair_prob, market_prob + edge * 0.8)
        else:
            # Our estimate lower than market - buy NO (short)
            decision = TradeDecision.BUY_NO
            target_price = min(1 - fair_prob, 1 - market_prob + abs(edge) * 0.8)

        # Order type decision
        # From autopredict: edge_to_spread_ratio >= 3 AND edge >= aggressive_edge → market order
        edge_to_spread_ratio = abs(edge) / spread_pct if spread_pct > 0 else 0
        aggressive_edge = abs(edge) > 0.10  # 10%+ edge is aggressive

        if edge_to_spread_ratio >= self.aggressive_edge_mult and aggressive_edge:
            order_type = "market"
            limit_price = None
        elif time_to_expiry_hours <= 12 and abs(edge) > 0.05:
            # Near expiry and decent edge - use market order
            order_type = "market"
            limit_price = None
        else:
            # Default to limit order
            order_type = "limit"
            limit_price = target_price

        # Position sizing
        # From autopredict: edge_scale = edge / min_edge (capped 2.5x)
        edge_scale = min(2.5, abs(edge) / self.min_edge)
        bankroll_cap = bankroll * self.bankroll_fraction * edge_scale
        depth_cap = liquidity_depth * 0.1  # Max 10% of liquidity

        size_usd = min(bankroll_cap, depth_cap)
        size_usd = max(10.0, size_usd)  # Minimum $10 trade

        # Risk-reward ratio (for buy YES: profit = (1 - market_prob) / market_prob)
        if decision == TradeDecision.BUY_YES:
            risk_reward_ratio = (
                (1 - market_prob) / market_prob if market_prob > 0.01 else 1.0
            )
        else:
            # For buy NO: profit = market_prob / (1 - market_prob)
            risk_reward_ratio = (
                market_prob / (1 - market_prob) if market_prob < 0.99 else 1.0
            )

        # Estimated fill rate
        fill_rate = 0.9 if order_type == "market" else 0.7

        # Rationale
        rationale_lines = [
            f"Edge: {edge:+.1%} (fair: {fair_prob:.1%}, market: {market_prob:.1%})",
            f"Decision: {decision.value}",
            f"Size: ${size_usd:.0f} ({self.bankroll_fraction:.0%} of bankroll)",
        ]
        if order_type == "limit":
            rationale_lines.append(f"Limit: {limit_price:.2f}")
        rationale_lines.append(f"Confidence: {estimate.confidence}%")

        return AutopredictExecution(
            decision=decision,
            market_id=estimate.market_id,
            size_usd=size_usd,
            order_type=order_type,
            limit_price=limit_price,
            rationale="\n".join(rationale_lines),
            edge=edge,
            spread_pct=spread_pct,
            estimated_fill_rate=fill_rate,
            risk_reward_ratio=risk_reward_ratio,
        )

    def get_execution_plan(
        self,
        theme: Optional[str] = None,
        bankroll: float = 10000.0,
        max_trades: int = 3,
    ) -> list[dict[str, Any]]:
        """Get complete execution plan for trading.

        This is the main entry point for autopredict integration:
        1. Generate fair_prob estimates from analysis
        2. Evaluate each trade opportunity
        3. Return sorted list of actionable trades

        Args:
            theme: Optional theme to focus on
            bankroll: Trading bankroll
            max_trades: Maximum number of trades to return

        Returns:
            List of trade dictionaries with execution parameters
        """
        logger.info(f"Generating execution plan for theme: {theme or 'all'}")

        # Step 1: Generate fair probability estimates
        estimates = self.generate_fair_prob_estimates(theme)

        if not estimates:
            logger.warning("No fair probability estimates generated")
            return []

        # Step 2: Evaluate each trade
        trades = []
        for estimate in estimates:
            execution = self.evaluate_trade(estimate, bankroll=bankroll)
            if execution.decision not in (TradeDecision.SKIP, TradeDecision.WAIT):
                trades.append(
                    {
                        "estimate": asdict(estimate),
                        "execution": asdict(execution),
                        "combined_score": abs(estimate.edge)
                        * estimate.confidence
                        / 100,
                    }
                )

        # Step 3: Sort by combined score and return top trades
        trades.sort(key=lambda t: t["combined_score"], reverse=True)

        return trades[:max_trades]

    def _estimate_fair_prob(
        self,
        question: str,
        market_prob: float,
        theme: Optional[str] = None,
    ) -> tuple[Optional[float], int, str]:
        """Estimate fair probability for a market question.

        This is simplified - in production would use:
        1. LLM analysis of the question
        2. Historical event base rates
        3. Geopolitical analysis integration

        Args:
            question: Market question
            market_prob: Current market probability
            theme: Optional theme filter

        Returns:
            (fair_prob, confidence, thesis) or (None, 0, "") if no estimate
        """
        question_lower = question.lower()

        # Theme-specific adjustments
        base_adjustment = 0.0
        confidence = 50
        thesis_parts = []

        # Iran-related markets
        if "iran" in question_lower:
            if "ceasefire" in question_lower:
                base_adjustment = -0.05  # Slightly less likely than market thinks
                thesis_parts.append("Historical ceasefire negotiations often fail")
                confidence = 60
            elif "enter" in question_lower or "invasion" in question_lower:
                base_adjustment = +0.03  # Slightly more likely
                thesis_parts.append("Escalation pattern suggests higher probability")
                confidence = 55
            elif "regime" in question_lower:
                base_adjustment = -0.08  # Less likely
                thesis_parts.append("Regime change is historically rare")
                confidence = 65

        # Oil-related markets
        elif "oil" in question_lower or "crude" in question_lower:
            if "100" in question_lower or "120" in question_lower:
                base_adjustment = +0.10  # Higher probability in tension
                thesis_parts.append("Geopolitical tension supports higher prices")
                confidence = 70
            elif "80" in question_lower or "70" in question_lower:
                base_adjustment = -0.05  # Lower probability during tension
                thesis_parts.append("Tension makes low prices less likely")
                confidence = 65

        # War/conflict markets
        elif "war" in question_lower or "conflict" in question_lower:
            base_adjustment = +0.02
            thesis_parts.append("Conflict resolution often takes longer than expected")
            confidence = 50

        # Apply adjustment
        fair_prob = market_prob + base_adjustment
        fair_prob = max(0.05, min(0.95, fair_prob))  # Clamp to 5-95%

        # Skip if no meaningful adjustment
        if abs(base_adjustment) < 0.01:
            return None, 0, ""

        thesis = f"Base rate adjustment: {'+'.join(thesis_parts) if thesis_parts else 'Market-conservative estimate'}"
        if theme and theme.lower() not in question_lower:
            confidence = int(confidence * 0.7)  # Lower confidence if theme mismatch

        return fair_prob, confidence, thesis


# Singleton instance
autopredict_adapter = AutopredictAdapter()
