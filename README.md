# Atlas IBKR Paper Trader

> **Multi-agent, AI-powered ETF trading decision system for Interactive Brokers paper accounts.**

An end-to-end research-to-order pipeline inspired by the ATLAS autoresearch architecture. This system coordinates **bull/bear debate agents**, **geopolitical sentiment analysis** (via Polymarket prediction markets), **ML-powered technical models** (Qlib LightGBM), **multi-DCF valuation**, and **4-layer signal orchestration** — all wrapped in a hard risk engine and human-approval gate. Paper trading only. Fail-closed on live mode.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run standalone analysis (no IBKR needed)
python analysis_standalone.py --ticker SPY

# Or run the full pipeline (stub mode — no TWS needed)
python run_daily.py

# Full integrated system with sample data
python integrated_trading_system.py --tickers XLE XAR USO --theme iran
```

---

## What This System Does

### Core Capability
Transform market data into **risk-checked, human-approved, paper-only order intents** for ETF trading via Interactive Brokers.

### The Pipeline
```
Market Data → Multi-Agent Research → 4-Layer Signal Orchestrator
  → Risk Engine (hard limits) → Human Approval Gate → IBKR Paper Adapter
```

Every stage produces typed, audit-logged artifacts. The system never trades autonomously — it always requires a human to approve before any paper order is submitted.

### Key Features

| Feature | Description |
|---|---|
| **Multi-Agent Debate** | Bull vs bear researchers argue theses; research manager judges |
| **Geopolitical Sentiment** | Polymarket prediction markets → sector-level sentiment signals |
| **4-Layer Signal Pipeline** | Macro → Sector → Superinvestor → Decision |
| **5-Strategy Technical Ensemble** | Trend, Mean Reversion, Momentum, Volatility, Stat Arb |
| **Qlib ML Model (optional)** | LightGBM-based price prediction with hybrid fallback |
| **Multi-DCF Valuation** | 5 methodologies: DCF, Owner Earnings, EV/EBITDA, Residual Income, DDM |
| **Experiential Memory** | BM25-based trade outcome retrieval — learns from past decisions |
| **Correlation-Adjusted Risk** | Volatility, cross-correlation & sector concentration position sizing |
| **3-Persona Risk Debate** | Aggressive, Conservative, Neutral analysts vote on each trade |
| **Hard Risk Engine** | 1.25x leverage cap, 12.5% position limit, 30% sector cap, 2.5% daily stop |
| **Human Approval Gate** | Token-based approval with replay protection |
| **Paper-Only Lock** | Hard fail-closed: live mode blocked at the config level |
| **Autoresearch Loop** | Scorecard → policy update → replay evaluation → keep/revert |

---

## Architecture

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Market Data Sources                          │
│  TWS (live) · yfinance (free/delayed) · Fixtures (tests)       │
└──────────┬──────────────────────────────────────┬──────────────┘
           │                                      │
           ▼                                      ▼
┌──────────────────────┐              ┌──────────────────────────┐
│  Multi-Agent Debate  │              │ 4-Layer Signal Pipeline  │
│                      │              │                          │
│  BullResearcher  ─┐  │              │ Layer 1: Macro Context   │
│                   │  │              │ Layer 2: Sector Ranking  │
│  BearResearcher ──┤  │              │ Layer 3: Superinvestor   │
│                   ├──►              │ Layer 4: Decision        │
│  GeoPolitical   ──┘  │              │                          │
│  (Polymarket)        │              │ → Recommendations        │
│                      │              │                          │
│  → InvestmentPlan    │              └──────────┬───────────────┘
└──────────────────────┘                         │
                                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Risk Engine                                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Hard Limits  │  │ Correlation  │  │ 3-Persona Debate     │  │
│  │ • Leverage   │  │ Adjusted     │  │ • Aggressive (0.8)   │  │
│  │ • Position   │  │ Position     │  │ • Conservative (0.3) │  │
│  │ • Sector     │  │ Sizing       │  │ • Neutral (0.5)      │  │
│  │ • Stop Loss  │  │              │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                            │                                    │
│                   → RiskVerdict (PASS/REJECT/REVIEW)           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                Human Approval Gate                              │
│                                                                 │
│  ProposedIntent → [Human Reviews] → ApprovalRecord (tokened)   │
│                                                                 │
│  Replay protection: once approved/rejected, token is consumed   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              IBKR Paper Adapter                                 │
│                                                                 │
│  • Real TWS connection via ib_insync (port 7497)               │
│  • Stub mode fallback (no TWS needed)                           │
│  • Paper trading only — live blocked by policy                  │
│  • Pre-trade broker checks (buying power, connectivity)         │
│                                                                 │
│  → OrderSubmission → TWS Paper Account                          │
└─────────────────────────────────────────────────────────────────┘
```

### Module Map

```
atlas-ibkr-trader/
├── app/
│   ├── agents/                  # Multi-agent research system
│   │   ├── debate_orchestrator.py   # Coordinates bull/bear/geo debate
│   │   ├── bull_researcher.py       # Bullish case analysis
│   │   ├── bear_researcher.py       # Bearish case analysis
│   │   ├── research_manager.py      # Judges debate → InvestmentPlan
│   │   ├── geopolitical_agent.py    # Polymarket sentiment analysis
│   │   ├── technical_agent.py       # Pure technical indicators
│   │   ├── sophisticated_technical.py # 5-strategy ensemble
│   │   ├── qlib_model_adapter.py    # ML model (LightGBM) adapter
│   │   └── research_note.py         # Shared data types
│   │
│   ├── layers/                  # 4-layer signal pipeline
│   │   ├── layer1_macro.py          # Macro regime assessment
│   │   ├── layer2_sector.py         # Sector ranking
│   │   ├── layer3_superinvestors.py # Philosophy reweighting
│   │   ├── layer4_decision.py       # Final decision aggregation
│   │   └── macro_thematic.py        # Event → sector mapping
│   │
│   ├── risk/                    # Risk management
│   │   ├── correlation_risk_manager.py  # Vol/corr/sector sizing
│   │   ├── debate_risk_manager.py      # 3-persona risk vote
│   │   └── personas.py                # Aggressive/Conservative/Neutral
│   │
│   ├── data/                    # Market data sources
│   │   ├── market_data.py           # Unified provider (TWS + yfinance)
│   │   ├── providers.py             # Abstract + fixture/mock providers
│   │   ├── polymarket_client.py     # Polymarket prediction markets
│   │   ├── qlib_data_loader.py      # Qlib data preparation
│   │   └── vendor_router.py         # Data source routing
│   │
│   ├── memory/                  # Experiential learning
│   │   ├── financial_memory.py     # BM25-based trade memory
│   │   └── reflection.py           # Post-trade reflection system
│   │
│   ├── valuation/               # Fundamental valuation
│   │   └── multi_dcf.py            # 5-methodology DCF engine
│   │
│   ├── portfolio/               # Portfolio management
│   │   └── llm_portfolio_manager.py # Coordinated multi-analysis
│   │
│   ├── execution/               # Prediction market execution
│   │   └── autopredict_adapter.py   # Polymarket trade execution
│   │
│   ├── pipeline/                # Pipeline orchestration
│   │   ├── daily_runner.py         # Full daily pipeline
│   │   └── run_daily.py            # CLI entry point
│   │
│   ├── config.py                # Pydantic config + paper-only lock
│   ├── schemas.py               # Event schemas (recommendation, risk, order)
│   ├── universe.py              # ETF catalog with leverage metadata
│   ├── signal_orchestrator.py   # 4-layer signal coordinator
│   ├── risk_engine.py           # Hard risk limit enforcement
│   ├── approval_gate.py         # Human approval with replay protection
│   ├── ibkr_adapter.py          # TWS connectivity + stub fallback
│   ├── intent_translator.py     # Recommendation → ProposedIntent
│   └── no_trade_controller.py   # Stale data → no-trade
│
├── configs/layers/              # Layer configuration YAMLs
├── fixtures/                    # Test fixtures (config, universe, market data)
├── tests/                       # pytest test suite
│   ├── layers/                  # Layer unit tests
│   ├── integration/             # Integration tests
│   └── autoresearch/            # Autoresearch loop tests
│
├── scripts/                     # Qlib model preparation scripts
├── analysis_standalone.py       # Standalone analysis (no TWS)
├── integrated_trading_system.py # Full integrated system
├── run_daily.py                 # Daily paper runner
└── pyproject.toml               # Project config + dependencies
```

---

## Running Modes

### 1. Standalone Analysis (No IBKR)
```bash
python analysis_standalone.py --ticker SPY
python analysis_standalone.py --income          # Income ETF analysis
python analysis_standalone.py --weekly           # Weekly payer ETF analysis
python analysis_standalone.py --memory           # Show learned experiences
```

Uses **yfinance** for free, delayed (~15min) market data. No TWS or IB Gateway needed. Perfect for research and signal generation.

### 2. Daily Pipeline (Stub Mode — No TWS)
```bash
python run_daily.py
```

Runs the full pipeline with a simulated IBKR adapter. Generates signals, runs the debate, produces recommendations. All orders are logged but never sent to a broker.

### 3. Daily Pipeline (With TWS Paper Account)
1. Start TWS in **Paper Trading Mode** (port 7497)
2. Ensure API connections are enabled in TWS settings
3. Run:
```bash
python run_daily.py
```

The system will detect the TWS connection and switch from stub to live paper mode automatically.

### 4. Integrated System (Full Demo)
```bash
python integrated_trading_system.py \
    --tickers XLE XAR USO \
    --theme iran \
    --portfolio-value 100000 \
    --execute               # Submits paper orders (requires TWS)
```

Runs all analysis layers: technical ensemble, geopolitical, multi-DCF valuation, macro-thematic, and correlation-adjusted risk — then recommends positions with sizing.

### 5. CLI Pipeline Runner
```bash
python -m app.pipeline.run_daily --help
python -m app.pipeline.run_daily --mode paper --fixture fixtures/config.paper.yaml
```

Structured pipeline with stage-gated execution (`--stage pre_exec`, `risk`, `approval`, `submit`).

---

## Risk Controls

| Limit | Value | Enforced By |
|---|---|---|
| Max gross leverage | 1.25x | Risk Engine + Config |
| Max position size | 12.5% of portfolio | Risk Engine |
| Max sector concentration | 30% | Risk Engine |
| Daily loss stop | 2.5% | Risk Engine |
| Execution mode | Paper only (hard lock) | Config validation |
| Human approval | Required | Approval Gate |
| Stale data | No-trade (fail-closed) | NoTradeController |

All limits are configurable in `fixtures/config.paper.yaml`.

---

## Dependencies

| Dependency | Purpose | Required |
|---|---|---|
| `ib-insync>=0.9.85` | TWS/IBKR connectivity | Optional (for live paper) |
| `pydantic>=2.0` | Config and schema validation | Required |
| `pyyaml>=6.0` | Config/universe file loading | Required |
| `pytest>=7.0` | Testing | Development |
| `rank-bm25>=0.2.2` | Financial memory retrieval | Optional (fallback to recency) |
| `yfinance` | Free market data | Optional (for standalone mode) |

---

## Project Status

This system is a **production-style paper-trading decision support system**. It is not financial advice. All trading is paper-only and requires human approval at every step.

- ✅ Multi-agent debate research pipeline
- ✅ 4-layer signal orchestration
- ✅ Hard risk engine with effective exposure accounting
- ✅ Human approval gate with replay protection
- ✅ IBKR paper adapter with stub fallback
- ✅ Standalone analysis (no TWS needed)
- ✅ Experiential learning memory (BM25)
- ✅ Qlib ML model integration (optional)
- ✅ Polymarket geopolitical sentiment
- ✅ Correlation-adjusted risk management
- ✅ 3-persona risk debate
- ✅ Comprehensive test suite
- ❌ Autonomous live trading (intentionally blocked)

---

## License & Credits

**Inspired by:**
- [atlas-gic](https://github.com/chrisworsey55/atlas-gic) — ATLAS autoresearch architecture
- [TradingAgents](https://github.com/kairi003/TradingAgents) — Multi-agent debate, memory, risk personas
- [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) — Technical ensemble, risk management, valuation
- [QuantAgent](https://github.com/QuantAgent/QuantAgent) — Technical indicators with SHORT signals

---

## ⚠️ Disclaimers

- **Paper trading only.** This system has a hard fail-closed lock preventing live trading.
- **Not financial advice.** This is an experimental research tool.
- **No warranty.** Use at your own risk. Past performance does not guarantee future results.
