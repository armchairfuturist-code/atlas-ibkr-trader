# Atlas — AI-Powered Investment Research System

> **Multi-agent research, narrative intelligence, and portfolio analysis — no broker required.**

An open-source investment research platform that coordinates **bull/bear debate agents**, **geopolitical sentiment analysis**, **ML-powered technical models**, **multi-DCF valuation**, **4-layer signal orchestration**, and a **narrative context framework** — all wrapped in a hard risk engine. Works with or without Interactive Brokers.

**Core philosophy:** Markets compress narratives into prices faster than fundamentals can verify. This system is designed to read that compression, detect when the market's model is desynchronizing from reality, and surface the gap.

---

## Quick Start — No Account Needed

```bash
# Install
pip install pydantic pyyaml pytest yfinance

# Analyze a single ticker (uses yfinance — free, delayed ~15min)
python analysis_standalone.py --ticker SPY

# Analyze income ETFs
python analysis_standalone.py --income

# Run the full multi-agent debate pipeline (stub mode)
python run_daily.py

# View the narrative context framework
cat docs/NARRATIVE_CONTEXT.md
```

**Everything above works with zero configuration, no accounts, no API keys.**

---

## What This System Does

### Core Capability
Generate **multi-dimensional investment research signals** by combining:
- Multi-agent bull/bear debate
- 5-strategy technical ensemble (Trend, Momentum, Mean Reversion, Volatility, Stat Arb)
- Geopolitical sentiment from Polymarket prediction markets
- 4-layer macro → sector → superinvestor → decision signal pipeline
- Multi-DCF valuation (5 methodologies)
- BM25 experiential memory (learns from past trade outcomes)
- Narrative lifecycle phase detection (pre-discovery → exhaustion)

**Optionally** (requires IBKR TWS):
- Read-only portfolio holdings query
- Paper trading execution with hard risk limits and human approval

### The Pipeline
```
Market Data → Multi-Agent Research → 4-Layer Signal Orchestrator
  → Risk Engine → Human Approval → Execution (optional)
```

Every stage produces typed, audit-logged artifacts. The system never trades autonomously.

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
| **13F Smart Money Tracker** | Compare system signals against any fund's SEC filings |
| **Vibe-Trading Integration** | Backtest recommendations, export to TradingView/Pine Script |
| **Freqtrade Optimization** | ML-driven parameter optimization via genetic algorithms |
| **Portfolio Holdings Query** | Read-only TWS connection to fetch actual positions with P&L |
| **Autoresearch Loop** | Scorecard → policy update → replay evaluation → keep/revert |

---

## Narrative Context

> **This project has a philosophical backbone.** Every analysis, every signal, every recommendation is informed by a narrative framework encoded in [`docs/NARRATIVE_CONTEXT.md`](docs/NARRATIVE_CONTEXT.md).

Markets are not just numbers. They are compression engines — they take the vast shape of the future and reduce it to a price. The system's prediction tools are designed to read this compression, detect when the market's model is desynchronizing from reality, and surface the gap.

The framework is built on four universal dynamics — **Efficiency of Intelligence**, **Compression**, **Coherence**, and **Selection** — that govern everything from neural architectures to energy transitions to financial markets. These are integrated with Leopold Aschenbrenner's *Situational Awareness* thesis (OOMs framework, trillion-dollar cluster buildout, AI power requirements going from 1%→20%+ of US electricity by 2030).

**What this means for anyone using the repo:**
- A "BUY" signal on a stock in the *priced-in* phase of its narrative lifecycle is weaker than a "HOLD" on a stock in *pre-discovery*
- The largest opportunities sit in coherence gaps — parts of the AI value chain that have desynchronized from each other (e.g., photonics stocks up 400% while power stocks are down 20%)
- The 13F tracker (`app/track_13f.py`) lets you compare our system's signals against smart money positions from any filer, seeded with Situational Awareness LP ($5.5B AUM)

**Read the full framework:** [`docs/NARRATIVE_CONTEXT.md`](docs/NARRATIVE_CONTEXT.md)

---

## Architecture

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Market Data Sources                          │
│  yfinance (free, delayed) · TWS (live) · Fixtures (tests)      │
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
│                   Analysis & Risk Engine                        │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Technical    │  │ 5-Strategy   │  │ Narrative Lifecycle  │  │
│  │ Indicators   │  │ Ensemble     │  │ Phase Detection      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Risk Engine  │  │ BM25 Memory  │  │ 13F Smart Money      │  │
│  │ (hard caps)  │  │ (past trades)│  │ Comparison Engine    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                            │                                    │
│                   → Research Signals + Risk Verdicts            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Output (choose your own adventure)                             │
│                                                                 │
│  • CLI analysis report   • TradingView (via Vibe-Trading)       │
│  • IBKR paper order      • CSV/JSON export                     │
│  • Pine Script strategy   • Manual trade (your own broker)     │
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
│   ├── no_trade_controller.py   # Stale data → no-trade
│   ├── track_13f.py             # 13F smart money tracker (Aschenbrenner seeded)
│   ├── vibe_bridge.py           # Vibe-Trading backtest + swarm + export bridge
│   ├── freq_bridge.py           # Freqtrade hyperopt + backtest integration
│   └── holdings_query.py        # Read-only IBKR positions/orders query
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

### 6. Backtest Recommendations (Vibe-Trading Integration)
```bash
# Requires Python 3.11 venv for direct engine mode
.vibe-venv\Scripts\pip install vibe-trading-ai

# Backtest one of our receiver-company picks
python -m app.vibe_bridge recommend --ticker TLN --conviction 67 --sector POWER

# Run multi-agent research swarm
python -m app.vibe_bridge swarm --preset investment_committee --target "TLN AI power thesis"

# Start API server
python -m app.vibe_bridge serve --port 8899
```

Leverages [Vibe-Trading](https://github.com/HKUDS/Vibe-Trading)'s 7 backtest engines, 74 research skills, and 29 multi-agent swarms for deep strategy validation and Pine Script export to TradingView.

### 7. Query IBKR Holdings (Read-Only)
```bash
# Live TWS connection (port 7496 = live, 7497 = paper)
python -m app.holdings_query --connect --port 7496 --save portfolio.json --scan

# Or load from file and scan against recommendations
python -m app.holdings_query --from-json portfolio.json --scan

# Stub mode with demo data
python -m app.holdings_query --stub --scan
```

Read-only connection to fetch actual positions, P&L, and open orders. Cross-references against system recommendations to identify concentration risks and gaps. **Zero write paths — no order placement capability.**

### 8. Track Smart Money (13F Filings)
```bash
python -m app.track_13f --report
```

Compares our system's signals against SEC 13F filings from smart money managers. Seeded with Situational Awareness LP (Leopold Aschenbrenner, $5.5B AUM, +28.9% return). Extensible to any SEC filer.

### 9. Optimize Strategy Parameters (Freqtrade Integration)
```bash
# Install freqtrade
pip install freqtrade

# Optimize entry/exit parameters for any ticker using genetic algorithms
python -m app.freq_bridge hyperopt --ticker TLN --epochs 100

# Run backtest with optimized parameters
python -m app.freq_bridge backtest --ticker TLN

# Batch optimize all receiver-company picks
python -m app.freq_bridge optimize-all
```

Uses [freqtrade](https://github.com/freqtrade/freqtrade)'s hyperopt engine (genetic algorithm parameter optimization) to find optimal entry/exit thresholds for each ticker. Strategies are auto-generated based on our narrative lifecycle phase (pre-discovery, discovery, priced-in).

---

## Web UI — Scoping

A Dash-based web UI is designed but not yet built. Planned features:

| Feature | Description |
|---|---|
| **Portfolio Dashboard** | Live position tracking, P&L, sector exposure heatmap |
| **Signal Monitor** | Real-time BUY/SELL/HOLD signals with narrative phase overlay |
| **13F Comparison** | Visual comparison of our picks vs smart money holdings |
| **Backtest Viewer** | Equity curves, strategy performance metrics |
| **Limit Order Planner** | RSI-based limit price calculator with technical levels |

**Tech stack:** Dash + Plotly + Bootstrap (Python only, no JavaScript)

**Status:** Design complete, implementation pending. Contributions welcome.

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
| `pydantic>=2.0` | Config and schema validation | ✅ Yes |
| `pyyaml>=6.0` | Config/universe file loading | ✅ Yes |
| `yfinance` | Free market data (standalone mode) | ✅ Yes |
| `pytest>=7.0` | Testing | For contributors |
| `ib-insync>=0.9.85` | TWS/IBKR read-only holdings query | ❌ Optional — only for IBKR users |
| `rank-bm25>=0.2.2` | Financial memory retrieval | ❌ Optional — falls back to recency |
| `vibe-trading-ai` | Backtest engine + multi-agent swarms | ❌ Optional — Python 3.11 venv |
| `freqtrade` | Genetic algorithm parameter optimization | ❌ Optional — `pip install freqtrade` |

**Core install (works for everyone):**
```bash
pip install pydantic pyyaml yfinance
```

---

## Project Status

This system is an **open-source investment research platform**. It is not financial advice. All trading features are paper-only and require human approval at every step.

- ✅ Multi-agent debate research pipeline
- ✅ 5-strategy technical ensemble (Trend, Momentum, Mean Reversion, Volatility, Stat Arb)
- ✅ 4-layer signal orchestration (Macro → Sector → Superinvestor → Decision)
- ✅ Geopolitical sentiment from Polymarket prediction markets
- ✅ Multi-DCF valuation (5 methodologies)
- ✅ BM25 experiential memory (learns from past trade outcomes)
- ✅ Narrative lifecycle phase detection
- ✅ 13F smart money tracker (Situational Awareness LP seeded)
- ✅ Risk engine with configurable hard limits
- ✅ Vibe-Trading backtest integration (7 engines, 29 swarms)
- ✅ Freqtrade hyperopt integration (genetic algorithm optimization)
- ✅ Read-only IBKR holdings query (optional, TWS required)
- ✅ IBKR paper trading adapter (optional, TWS required)
- ✅ Japanese chemical/materials analysis (Tokyo Stock Exchange)
- ✅ Comprehensive test suite
- ❌ Autonomous live trading (intentionally blocked)

---

## License & Credits

**Inspired by:**
- [atlas-gic](https://github.com/chrisworsey55/atlas-gic) — ATLAS autoresearch architecture
- [TradingAgents](https://github.com/kairi003/TradingAgents) — Multi-agent debate, memory, risk personas
- [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) — Technical ensemble, risk management, valuation
- [QuantAgent](https://github.com/QuantAgent/QuantAgent) — Technical indicators with SHORT signals
- [freqtrade](https://github.com/freqtrade/freqtrade) — Genetic algorithm hyperopt engine

---

## ⚠️ Disclaimers

- **Not financial advice.** This is an experimental research tool. Nothing in this repository constitutes financial advice, investment recommendations, or solicitation to trade.
- **No warranty.** Use at your own risk. Past performance does not guarantee future results.
- **IBKR paper trading only.** The IBKR execution path has a hard fail-closed lock preventing live trading. If you connect this to a broker, use paper accounts only.
- **Data delays.** yfinance provides delayed (~15min) market data. For real-time data, use IBKR TWS with appropriate subscriptions.
