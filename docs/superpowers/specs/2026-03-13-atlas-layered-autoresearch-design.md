# Atlas layered autoresearch design

## Goal
Add a feedback loop to tune trading parameters automatically.

## Current state
The system currently uses static values. `app/signal_orchestrator.py:33` has the 4-layer structure but no learning capability. `app/config.py:28` is a fixed file. `app/risk_engine.py:50` and `app/approval_gate.py:22` provide safety but do not adapt.

## Why config mutation
Fixed thresholds stop working when market volatility or volume shifts. Mutating the configuration lets the system tune its own parameters based on performance without manual code changes.

## Target architecture
1. Universe: Dynamic asset filtering in `app/universe.py:65`.
2. Signal: Alpha generation in `app/signal_orchestrator.py:59`.
3. Risk: Exposure management in `app/risk_engine.py:50`.
4. Execution: Order placement in `app/ibkr_adapter.py:21`.

## New components
- `DecisionMemory`: persistent store for state, action, and reward data.
- `ScorecardEngine`: evaluates how well signals predicted price movement.
- `PolicyUpdater`: proposes new parameter values for scored agents.
- `ReplayEvaluator`: uses `app/test_harness.py:68` to backtest changes before deployment.

## Mutation and keep-revert model
The system generates a candidate, runs a backtest, and deploys it if successful. If performance drops below a threshold, it reverts to the previous version.

## Safety boundaries
Hard limits in `app/approval_gate.py:22` and `app/no_trade_controller.py:22` prevent mutations from creating unsafe configurations. Paper-only controls in `app/config.py:41` and `app/ibkr_adapter.py:33` remain outside the mutation surface.

## Data flow
The research cycle starts in `app/pipeline/daily_runner.py:98` after the market closes. Data flows from decision memory to the scorecard, then to the updater. Promoted configs feed the next paper run.

## Failure handling
If a mutation fails or errors, the system reverts to the last known good configuration. If replay data is incomplete, the candidate is discarded.

## Testing strategy
Add replay and mutation tests beyond the current baseline in `tests/test_bootstrap.py:1`, `tests/test_config.py:1`, and `tests/test_universe.py:1`. Keep deterministic fixtures anchored on `fixtures/universe.valid.yaml:1` and `app/test_harness.py:68`.

## Rollout plan
Start with shadow mode, move to paper trading with promoted configs, and only consider broader automation after replay stability is proven.

## Non-goals
This project does not cover changing core safety logic, adding new live-trading behavior, or depending on proprietary atlas-gic prompt files.

## File-level direction
Primary integration points are `app/signal_orchestrator.py:114`, `app/pipeline/daily_runner.py:98`, `app/schemas.py:47`, and new modules under `app/autoresearch/` and `app/layers/`.

## Recommended default
Start with shadow-mode learning, config mutation only, and replay-based keep-or-revert. Cap each mutation cycle to small bounded changes.
