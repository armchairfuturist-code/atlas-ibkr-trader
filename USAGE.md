# Usage Guide

This guide covers every way to run the Atlas IBKR Paper Trader — from standalone analysis to full paper trading with a TWS connection.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Commands](#quick-commands)
3. [Mode 1: Standalone Analysis (No IBKR)](#mode-1-standalone-analysis-no-ibkr)
4. [Mode 2: Daily Pipeline — Stub Mode](#mode-2-daily-pipeline--stub-mode)
5. [Mode 3: Daily Pipeline — Live Paper TWS](#mode-3-daily-pipeline--live-paper-tws)
6. [Mode 4: Integrated Multi-Analysis System](#mode-4-integrated-multi-analysis-system)
7. [Mode 5: CLI Pipeline Runner](#mode-5-cli-pipeline-runner)
8. [Configuration](#configuration)
9. [Risk Limits](#risk-limits)
10. [Qlib ML Setup (Optional)](#qlib-ml-setup-optional)
11. [Testing](#testing)

---

## Installation

### Prerequisites
- Python 3.11+
- (Optional) TWS or IB Gateway for live paper trading
- (Optional) Qlib for ML-enhanced predictions

### Install

```bash
# Clone the repo
git clone https://github.com/armchairfuturist-code/atlas-ibkr-trader.git
cd atlas-ibkr-trader

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install core dependencies
pip install pydantic pyyaml pytest

# Install optional dependencies
pip install ib-insync      # For TWS connectivity
pip install rank-bm25      # For BM25 memory retrieval
pip install yfinance       # For standalone market data
```

---

## Quick Commands

```bash
# Analyze a single ticker (no IBKR needed)
python analysis_standalone.py --ticker SPY

# Analyze income ETFs
python analysis_standalone.py --income

# Analyze weekly-paying ETFs
python analysis_standalone.py --weekly

# Run daily pipeline (stub mode — no TWS)
python run_daily.py

# Full integrated analysis with sample data
python integrated_trading_system.py --tickers XLE XAR USO --theme iran

# Run tests
pytest -q

# Show CLI help
python -m app.pipeline.run_daily --help
```

---

## Mode 1: Standalone Analysis (No IBKR)

The standalone script **`analysis_standalone.py`** uses yfinance for free, delayed (~15min) market data. No TWS, no IB Gateway, no API keys needed.

### Analyze a Single Ticker

```bash
python analysis_standalone.py --ticker SPY
```

**What happens:**
1. Fetches price data from yfinance
2. Runs multi-agent bull/bear debate
3. Shows rating, conviction, bull/bear contribution split, thesis
4. Checks prior experiences from memory (BM25 similarity)

**Output:**
```
============================================================
ANALYSIS: SPY
============================================================

Price: $501.23
P/E: 24.5 | Dividend Yield: 1.32%
1M Return: +2.34%
3M Return: +5.67% | Volatility: 12.3%

--- Multi-Agent Debate ---
Rating: BUY
Conviction: 78
Bull/Bear: 65%/35%
Thesis: Strong momentum with oversold RSI bounce...

--- Similar Past Experiences ---
  No prior experiences on record
```

### Analyze Income ETFs

```bash
python analysis_standalone.py --income
```

Analyzes 8 income ETFs: JEPI, JEPQ, SCHD, VYM, HDV, QYLD, XYLD, DGRO. Sorts by Sharpe ratio (risk-adjusted return).

### Analyze Weekly-Paying ETFs

```bash
python analysis_standalone.py --weekly
```

Analyzes covered-call and options-income ETFs: QYLD, XYLD, SPYD, DIV, MSTY, NVDY, TSLY, AMZY.

### View Learned Experiences

```bash
python analysis_standalone.py --memory
```

Shows all stored trade outcomes with lessons learned, searchable via BM25 text retrieval.

### Log a Trade (For Learning)

```bash
python analysis_standalone.py --log-trade SPY LONG BUY 85 +3.2 14
```

Logs a trade outcome: ticker=SPY, direction=LONG, rating=BUY, conviction=85, PnL=+3.2%, held=14 days. The system derives a lesson and stores it in memory.

---

## Mode 2: Daily Pipeline — Stub Mode

No TWS needed. The IBKR adapter runs in **stub mode** — it logs orders but never sends them anywhere.

```bash
python run_daily.py
```

**What happens:**
1. Connects in stub mode (simulated)
2. Loads the ETF universe
3. Generates signals through all 4 layers
4. Runs multi-agent debate on top signals
5. Shows recommendation and asks for approval
6. If approved, creates a simulated order

**Output:**
```
============================================================
ATLAS Paper Trading - Daily Runner
============================================================
WARNING: Running in STUB mode (TWS not connected)
Start TWS with API enabled for live trading

Running pipeline...
Result: completed
  Config loaded
  Universe loaded (14 ETFs)
  Signals generated

14 Signals Generated:
  QQQ: LONG @ conviction=82 (OVERWEIGHT)
  XLF: LONG @ conviction=75 (OVERWEIGHT)
  XLE: LONG @ conviction=71 (BUY)
  ...

Top Signal Analysis (Multi-Agent Debate):
  Ticker: QQQ
  Rating: BUY (conviction=78)
  Bull/Bear: 70%/30%
  Thesis: Technology sector momentum with macro tailwinds...

>>> Submit paper order for QQQ? (y/n)
```

---

## Mode 3: Daily Pipeline — Live Paper TWS

### Step 1: Start TWS in Paper Mode

1. Open **TWS** or **IB Gateway**
2. Log in with your **paper trading credentials** (separate from live account)
3. Go to **Settings → API → Configuration**
4. Check **"Enable ActiveX and Socket Clients"**
5. Ensure port is set to **7497** (paper default)
6. Check **"Allow connections from localhost only"**

### Step 2: Run the Pipeline

```bash
python run_daily.py
```

**Without stub mode:**
```
============================================================
ATLAS Paper Trading - Daily Runner
============================================================
Connected to TWS (Paper Mode)
  Net Liquidation: $100,000.00
  Buying Power: $200,000.00

Running pipeline...
...
>>> Submit paper order for QQQ? (y/n) y
ORDER SUBMITTED: PAPER-123456
  QQQ LONG 100 shares
  Check TWS to approve/fill order
```

### TWS Setup Checklist

- [ ] TWS running in **Paper Mode** (not live)
- [ ] API connections enabled
- [ ] Port **7497** open on firewall (localhost only)
- [ ] Account starts with `DU` prefix
- [ ] Environment variables optional (defaults work out of box)

---

## Mode 4: Integrated Multi-Analysis System

The **`integrated_trading_system.py`** script combines all analysis engines into one run.

```bash
# Analysis only (no orders)
python integrated_trading_system.py \
    --tickers XLE XAR USO \
    --theme iran

# With paper order execution
python integrated_trading_system.py \
    --tickers XLE XAR USO \
    --theme iran \
    --portfolio-value 100000 \
    --execute
```

**Analysis layers run:**
1. **Sophisticated Technical** — 5-strategy ensemble (Trend, Momentum, Mean Reversion, Volatility, Stat Arb)
2. **Geopolitical Sentiment** — Polymarket prediction market data
3. **Multi-DCF Valuation** — 5 valuation methodologies
4. **Macro-Thematic Mapping** — Event → sector impact
5. **Correlation-Adjusted Risk** — Position sizing with volatility/correlation adjustments

**Output includes per-ticker breakdown:**
```
1. XLE - BUY
   Shares: 143
   Entry: $85.50
   Stop Loss: $78.66
   Target: $98.33
   Confidence: 78%
   Conviction Score: 54.7

   Component Scores:
     Technical: +45.0
     Geopolitical: +15.0
     Valuation: +30.0
     Macro: +25.0
```

---

## Mode 5: CLI Pipeline Runner

```bash
python -m app.pipeline.run_daily --help
python -m app.pipeline.run_daily --mode paper
python -m app.pipeline.run_daily --mode paper --fixture fixtures/config.paper.yaml
```

**Options:**
| Flag | Description |
|---|---|
| `--mode paper/live` | Execution mode (live blocked by policy) |
| `--fixture PATH` | Market data fixture file |
| `--stage NAME` | Run up to specific stage (`pre_exec`, `risk`, `approval`, `submit`) |

---

## Configuration

### Main Config File: `fixtures/config.paper.yaml`

```yaml
mode: paper
risk_limits:
  max_gross_leverage: 1.25
  max_position_pct: 12.5
  max_sector_pct: 30.0
  daily_loss_stop_pct: 2.5
ibkr_host: 127.0.0.1
ibkr_port: 7497
ibkr_client_id: 1
require_human_approval: true
```

### ETF Universe: `fixtures/universe.valid.yaml`

Defines the tradable universe with leverage metadata:

```yaml
version: "1.0"
etfs:
  - ticker: SPY
    name: SPDR S&P 500 ETF
    etf_type: unlevered
    primary_sector: broad_market
    leverage_factor: 1.0
    min_adverage_volume: 80000000

  - ticker: TQQQ
    name: ProShares UltraPro QQQ
    etf_type: levered_2x
    primary_sector: technology
    leverage_factor: 3.0        # 3x leveraged
    min_adverage_volume: 5000000

  - ticker: SH
    name: ProShares Short S&P 500
    etf_type: inverse
    primary_sector: broad_market
    leverage_factor: -1.0       # Inverse (short)
    min_adverage_volume: 3000000
```

### Layer Configs: `configs/layers/base/`

```bash
configs/layers/base/
├── layer1_macro.yaml        # Macro context weights & thresholds
├── layer2_sector.yaml       # Sector ranking parameters
├── layer3_superinvestors.yaml  # Philosophy reweighting config
└── layer4_decision.yaml     # Decision aggregation rules
```

---

## Risk Limits

All limits are enforced server-side by the `RiskEngine` and `DebateRiskManager`. Configurable in YAML.

| Limit | Default | Description |
|---|---|---|
| `max_gross_leverage` | 1.25x | Maximum gross exposure / equity (effective, not notional) |
| `max_position_pct` | 12.5% | Single position as % of portfolio |
| `max_sector_pct` | 30.0% | Single sector as % of portfolio |
| `daily_loss_stop_pct` | 2.5% | Daily P&L loss triggers automatic halt |

**Reject Codes** (machine-readable):
| Code | Meaning |
|---|---|
| `GROSS_LEVERAGE_BREACH` | Would exceed max leverage |
| `POSITION_SIZE_BREACH` | Position too large |
| `SECTOR_CONCENTRATION_BREACH` | Sector over-concentrated |
| `DAILY_STOP_TRIGGERED` | Daily loss limit hit |
| `LIQUIDITY_INSUFFICIENT` | Not enough liquidity |
| `SPREAD_EXCEEDS_LIMIT` | Spread too wide |
| `DATA_STALE` | Market data too old |
| `DATA_MISSING` | Required data unavailable |
| `APPROVAL_REQUIRED` | Human approval not yet given |
| `LIVE_MODE_FORBIDDEN` | Live trading blocked by policy |

---

## Qlib ML Setup (Optional)

For ML-enhanced price predictions using Microsoft Qlib with LightGBM:

```bash
# Qlib requires Python 3.12 (not 3.14)
pip install pyqlib pandas numpy lightgbm

# Prepare data
python app/scripts/prepare_qlib_data.py

# Train model
python app/scripts/train_qlib_model.py

# Run backtest
python app/scripts/backtest_qlib.py
```

The system auto-detects Qlib availability. If unavailable, it gracefully falls back to the rule-based 5-strategy technical ensemble.

---

## Testing

```bash
# Run all tests
pytest -q

# Run specific test files
pytest tests/test_bootstrap.py -q
pytest tests/test_config.py -q
pytest tests/test_universe.py -q
pytest tests/layers/ -q
pytest tests/integration/ -q

# Run with coverage
pytest --cov=app -q
```

The test suite is designed to be **deterministic** — zero time-dependent nondeterminism. All tests use frozen timestamps and seeded randomness.

---

## Troubleshooting

### "ib_insync not available — using stub mode"
TWS is not running or `ib-insync` is not installed. The system continues in stub mode — analysis works, orders are logged but not submitted.

### "LIVE_MODE_FORBIDDEN"
The config has `mode: live`. Change to `mode: paper` in `fixtures/config.paper.yaml`. Live mode is intentionally blocked.

### "No module named 'yfinance'"
Install: `pip install yfinance`. Without it, standalone analysis won't fetch live data.

### TWS connection fails
- Is TWS in **Paper Mode**? (port 7497 not 7496)
- Are API connections enabled? (Settings → API → Enable ActiveX)
- Is TWS actually running? (not just the login screen)
- Firewall blocking port 7497?

### PermissionError on Windows
Run your terminal as Administrator, or check that the `.worktrees/` directory isn't read-only.
