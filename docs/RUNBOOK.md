# Atlas IBKR Paper Trading - Operational Runbook

## Safety First

**⚠️ IMPORTANT: This system is configured for PAPER TRADING ONLY**

- Live trading is BLOCKED by default
- Human approval is REQUIRED before any order submission
- Daily loss stop is enforced at 2.5%

---

## Pre-Run Checklist

- [ ] IBKR TWS or IB Gateway is running in **PAPER MODE**
- [ ] Paper trading is enabled in TWS (Settings → API → Paper Trading)
- [ ] Socket port is configured (default: 7497 for paper)
- [ ] Account shows as paper mode (starts with DU)

---

## Daily Operation

### 1. Start IBKR Paper

```bash
# Start TWS in paper mode (manual)
# Or use IB Gateway with paper credentials
```

### 2. Run Pipeline

```bash
# Navigate to project
cd ~/atlas-ibkr-trader

# Run full pipeline
python -m app.pipeline.daily_runner --mode paper

# Run to specific stage
python -m app.pipeline.daily_runner --mode paper --stage risk
```

### 3. Review Signals

The pipeline will output:
- Generated signals with conviction scores
- Risk evaluations for each signal
- Proposed order intents

### 4. Approve Orders

**Manual step required:**
- Review proposed intents
- Approve or reject each

### 5. Submit to IBKR (if approved)

```bash
# Submit approved orders
python -m app.pipeline.daily_runner --mode paper --stage submit
```

---

## Emergency Procedures

### Daily Stop Triggered
If daily loss exceeds 2.5%:
- Pipeline automatically enters NO_TRADE mode
- No new orders will be submitted
- Review portfolio and wait for next day

### IBKR Connection Lost
1. Check TWS/IB Gateway is running
2. Verify paper mode is enabled
3. Restart pipeline

### Margin Call Warning
- Monitor account equity vs margin requirements
- System will warn if approaching limits

---

## Configuration

Risk limits (editable in `config.yaml`):
- Max gross leverage: 1.25x
- Max position size: 12.5%
- Max sector concentration: 30%
- Daily loss stop: 2.5%

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "live mode blocked" | Ensure config.yaml has `mode: paper` |
| "DATA_STALE" | Check data provider connectivity |
| "APPROVAL_REQUIRED" | Human must approve before submit |
| Connection refused | Verify IBKR is running on correct port |

---

## IBKR Setup Reference

See full IBKR setup checklist in the plan: `atlas-gic-ibkr-paper-etf-margin.md`
