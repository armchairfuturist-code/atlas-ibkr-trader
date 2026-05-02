# TradingAgents-Inspired Improvements Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement each task.

**Goal:** Enhance atlas-ibkr-trader with TradingAgents patterns: vendor abstraction, multi-agent debate, memory system, and 5-tier ratings.

**Architecture:** Adding LLM-driven multi-agent analysis layer between signal generation and execution, with vendor abstraction for real market data.

**Tech Stack:** Python, LangChain/LangGraph patterns (simplified), rank-bm25 for memory

---

## Task 1: Vendor Abstraction Layer
**Files:**
- Modify: `app/data/providers.py`
- Create: `app/data/vendor_router.py`

- [ ] **Step 1: Add route_to_vendor function**

```python
# In vendor_router.py
VENDOR_REGISTRY = {
    "yfinance": YFinanceVendor(),
    "alpha_vantage": AlphaVantageVendor(),
    "ibkr": IBKRDataProvider(),  # Your existing provider
}

def route_to_vendor(method: str, vendor: str, *args, **kwargs):
    """Route data request to appropriate vendor with fallback."""
    primary = VENDOR_REGISTRY.get(vendor)
    if primary and hasattr(primary, method):
        return getattr(primary, method)(*args, **kwargs)
    # Fallback chain logic
```

- [ ] **Step 2: Add vendor interface abstraction**

```python
class DataVendor(ABC):
    @abstractmethod
    def get_stock_data(self, symbol: str, start: date, end: date) -> pd.DataFrame: pass
    @abstractmethod
    def get_indicators(self, symbol: str) -> dict: pass
    @abstractmethod
    def get_news(self, symbol: str) -> list[dict]: pass
    @abstractmethod
    def get_fundamentals(self, symbol: str) -> dict: pass
```

- [ ] **Step 3: Integrate into existing providers.py**

Add vendor routing to `IBKRDataProvider` so it can fall back to other vendors.

---

## Task 2: 5-Tier Conviction Scale
**Files:**
- Modify: `app/schemas.py`
- Modify: `app/signal_orchestrator.py`

- [ ] **Step 1: Add SignalRating enum to schemas.py**

```python
class SignalRating(str, Enum):
    """5-tier rating scale from TradingAgents."""
    BUY = "BUY"           # Strong conviction to enter/add
    OVERWEIGHT = "OVERWEIGHT"  # Favorable, gradually increase
    HOLD = "HOLD"         # Maintain current position
    UNDERWEIGHT = "UNDERWEIGHT"  # Reduce exposure
    SELL = "SELL"         # Exit position or avoid entry
```

- [ ] **Step 2: Update Recommendation schema**

```python
@dataclass
class Recommendation:
    # ... existing fields ...
    rating: SignalRating = SignalRating.HOLD  # NEW: 5-tier rating
    conviction: int = 50  # 1-100 scale
    position_size_pct: float = 0.0  # NEW: dynamic sizing based on conviction
```

- [ ] **Step 3: Update SignalOrchestrator to output ratings**

Map conviction ranges to ratings:
- 80-100 → BUY
- 65-79 → OVERWEIGHT
- 45-64 → HOLD
- 30-44 → UNDERWEIGHT
- 0-29 → SELL

Position size = base_size * (conviction / 50) with limits.

---

## Task 3: Multi-Agent Debate System
**Files:**
- Create: `app/agents/__init__.py`
- Create: `app/agents/bull_researcher.py`
- Create: `app/agents/bear_researcher.py`
- Create: `app/agents/research_manager.py`
- Create: `app/agents/debate_orchestrator.py`

- [ ] **Step 1: Create BullResearcher agent**

```python
class BullResearcher:
    """Agent that argues bullish case for a ticker."""
    def analyze(self, ticker: str, data: dict) -> ResearchNote:
        # Uses LLM to find bullish signals
        # Returns: thesis, confidence, key_points[]
```

- [ ] **Step 2: Create BearResearcher agent**

```python
class BearResearcher:
    """Agent that argues bearish case for a ticker."""
    def analyze(self, ticker: str, data: dict) -> ResearchNote:
        # Uses LLM to find bearish signals
```

- [ ] **Step 3: Create ResearchManager (judge)**

```python
class ResearchManager:
    """Judges bull/bear debate, creates investment plan."""
    def judge(self, bull_note: ResearchNote, bear_note: ResearchNote) -> InvestmentPlan:
        # Evaluates both sides
        # Outputs: rating, conviction, thesis
```

- [ ] **Step 4: Create DebateOrchestrator**

```python
class DebateOrchestrator:
    """Runs multi-round debate between bull/bear agents."""
    def __init__(self, max_rounds: int = 3):
        self.max_rounds = max_rounds
    
    def run_debate(self, ticker: str, data: dict) -> InvestmentPlan:
        # Round 1: Bull + Bear initial analysis
        # Round 2: Each responds to other's points
        # Round N: Research Manager judges
```

---

## Task 4: BM25 Memory System
**Files:**
- Create: `app/memory/__init__.py`
- Create: `app/memory/financial_memory.py`
- Create: `app/memory/reflection.py`

- [ ] **Step 1: Install rank-bm25 dependency**

```bash
pip install rank-bm25
```

- [ ] **Step 2: Create FinancialSituationMemory**

```python
from rank_bm25 import BM25Okapi

class FinancialSituationMemory:
    """BM25-based memory for past trading situations."""
    
    def __init__(self):
        self.situations: list[dict] = []
        self.bm25: Optional[BM25Okapi] = None
    
    def add_memory(self, situation: str, outcome: str, lesson: str):
        """Store a trading situation and its outcome."""
        self.situations.append({
            "situation": situation,
            "outcome": outcome,
            "lesson": lesson,
            "timestamp": datetime.now()
        })
        self._rebuild_index()
    
    def get_memories(self, current_situation: str, n: int = 3) -> list[dict]:
        """Retrieve similar past situations."""
        # Tokenize and search with BM25
        # Return top N matches with full context
```

- [ ] **Step 3: Create Reflection system**

```python
def reflect_and_remember(trade_result: dict):
    """After trade execution, store lessons learned."""
    memory = FinancialSituationMemory()
    
    situation = f"Ticker: {trade_result['ticker']}, "
    situation += f"Regime: {trade_result['macro_regime']}, "
    situation += f"Rating: {trade_result['rating']}"
    
    outcome = f"PnL: {trade_result['pnl_pct']:.2f}%, "
    outcome += f"Holding period: {trade_result['holding_days']} days"
    
    lesson = trade_result.get('lesson', 'No significant lesson')
    
    memory.add_memory(situation, outcome, lesson)
```

---

## Task 5: Risk Persona Debate
**Files:**
- Create: `app/risk/debate_risk_manager.py`
- Create: `app/risk/personas.py`
- Modify: `app/risk_engine.py`

- [ ] **Step 1: Create RiskPersona classes**

```python
@dataclass
class RiskPersona:
    name: str
    risk_tolerance: float  # 0-1
    position_size_mult: float  # multiplier on base size
    
class AggressiveAnalyst(RiskPersona):
    def __init__(self):
        super().__init__("Aggressive", risk_tolerance=0.8, position_size_mult=1.3)
    
class ConservativeAnalyst(RiskPersona):
    def __init__(self):
        super().__init__("Conservative", risk_tolerance=0.3, position_size_mult=0.7)
    
class NeutralAnalyst(RiskPersona):
    def __init__(self):
        super().__init__("Neutral", risk_tolerance=0.5, position_size_mult=1.0)
```

- [ ] **Step 2: Create DebateRiskManager**

```python
class DebateRiskManager:
    """3-way risk debate before final approval."""
    
    def __init__(self, portfolio_manager):
        self.personas = [AggressiveAnalyst(), ConservativeAnalyst(), NeutralAnalyst()]
        self.portfolio_manager = portfolio_manager
    
    def evaluate_with_debate(
        self, 
        recommendation: Recommendation,
        portfolio: PortfolioState
    ) -> RiskVerdictEvent:
        """Run risk debate and return portfolio manager's decision."""
        
        # Each persona evaluates independently
        persona_views = []
        for persona in self.personas:
            view = persona.evaluate(recommendation, portfolio)
            persona_views.append(view)
        
        # Portfolio manager synthesizes
        final_verdict = self.portfolio_manager.judge(
            recommendation, portfolio, persona_views
        )
        return final_verdict
```

- [ ] **Step 3: Integrate into existing risk_engine.py**

Add `evaluate_with_debate()` method that runs before the existing hard-limit checks.

---

## Task 6: Integration & Verification
**Files:**
- Modify: `app/signal_orchestrator.py` (integrate debate)
- Modify: `app/main.py` or `app/pipeline.py` (wire everything together)

- [ ] **Step 1: Wire debate system into SignalOrchestrator**

In `generate_signals()`, after Layer 4 decision, run:
```python
# Before returning recommendations
for rec in recommendations:
    debate_result = debate_orchestrator.run_debate(rec.ticker, market_data)
    rec.rating = debate_result.rating
    rec.conviction = debate_result.conviction
    rec.thesis = debate_result.thesis
```

- [ ] **Step 2: Wire memory system into pipeline**

After trade execution, call `reflect_and_remember()` to store the outcome.

- [ ] **Step 3: Run tests and verify**

```bash
cd .worktrees/implementation
python -m pytest tests/ -v
```

Expected: All existing tests pass, new tests for added components pass.

---

## Dependencies

```
rank-bm25>=0.2.2
```

## Integration Points

| Component | Integration Point |
|-----------|-------------------|
| Vendor Router | `data/providers.py` |
| 5-Tier Rating | `schemas.py`, `signal_orchestrator.py` |
| Debate System | `layers/` enhancement or new `agents/` module |
| BM25 Memory | New `memory/` module, called post-trade |
| Risk Debate | `risk_engine.py` enhancement |
