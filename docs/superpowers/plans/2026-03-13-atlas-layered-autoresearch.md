# Atlas layered autoresearch Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace placeholder signal logic with a config-backed four-layer ETF/sector decision stack and a shadow-mode autoresearch keep-or-revert loop.

**Architecture:** Keep existing hard safety controls in `app/risk_engine.py`, `app/approval_gate.py`, and `app/no_trade_controller.py`. Add small layer modules under `app/layers/` and offline learning modules under `app/autoresearch/`; the runtime path generates proposals, while the offline path scores outcomes, proposes one bounded change, replay-tests it, and promotes or reverts.

**Tech Stack:** Python 3.11, dataclasses, Pydantic models, YAML config/fixtures, pytest, existing IBKR paper adapter.

---

## File structure

Planned additions and modifications:

- Create: `app/layers/__init__.py`
- Create: `app/layers/models.py`
- Create: `app/layers/config_loader.py`
- Create: `app/layers/layer1_macro.py`
- Create: `app/layers/layer2_sector.py`
- Create: `app/layers/layer3_superinvestors.py`
- Create: `app/layers/layer4_decision.py`
- Create: `app/autoresearch/__init__.py`
- Create: `app/autoresearch/decision_memory.py`
- Create: `app/autoresearch/scorecard.py`
- Create: `app/autoresearch/policy_updater.py`
- Create: `app/autoresearch/replay_evaluator.py`
- Create: `app/autoresearch/versioning.py`
- Create: `configs/layers/base/layer1_macro.yaml`
- Create: `configs/layers/base/layer2_sector.yaml`
- Create: `configs/layers/base/layer3_superinvestors.yaml`
- Create: `configs/layers/base/layer4_decision.yaml`
- Create: `configs/layers/promoted/README.md`
- Create: `fixtures/replay/day_01.yaml`
- Create: `fixtures/replay/day_02.yaml`
- Create: `fixtures/replay/outcomes_01.yaml`
- Create: `tests/layers/test_layer1_macro.py`
- Create: `tests/layers/test_layer2_sector.py`
- Create: `tests/layers/test_layer3_superinvestors.py`
- Create: `tests/layers/test_layer4_decision.py`
- Create: `tests/autoresearch/test_decision_memory.py`
- Create: `tests/autoresearch/test_scorecard.py`
- Create: `tests/autoresearch/test_policy_updater.py`
- Create: `tests/autoresearch/test_replay_evaluator.py`
- Create: `tests/integration/test_layered_pipeline.py`
- Create: `tests/integration/test_shadow_mode_promotion.py`
- Modify: `app/schemas.py`
- Modify: `app/signal_orchestrator.py`
- Modify: `app/pipeline/daily_runner.py`
- Modify: `app/test_harness.py`
- Modify: `docs/RUNBOOK.md`

---

## Chunk 1: Layer contracts and configuration

### Task 1: Add shared layer output models

**Files:**
- Create: `app/layers/models.py`
- Modify: `app/schemas.py`
- Test: `tests/layers/test_layer1_macro.py`

- [ ] **Step 1: Write the failing test** for a `MacroAgentOutput` and `SectorDeskOutput` shape with required fields (`agent_name`, `confidence`, `config_version`, ETF/sector tags).
- [ ] **Step 2: Run test to verify it fails**.
  - Run: `pytest tests/layers/test_layer1_macro.py::test_macro_agent_output_schema -v`
  - Expected: FAIL due to missing model definitions.
- [ ] **Step 3: Write minimal implementation** using dataclasses (or Pydantic models matching existing style in `app/schemas.py`).
- [ ] **Step 4: Run test to verify it passes**.
  - Run: `pytest tests/layers/test_layer1_macro.py::test_macro_agent_output_schema -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/layers/models.py app/schemas.py tests/layers/test_layer1_macro.py`
  - `git commit -m "feat(layers): add shared layer output contracts"`

### Task 2: Add versioned layer config loader and base YAMLs

**Files:**
- Create: `app/layers/config_loader.py`
- Create: `configs/layers/base/layer1_macro.yaml`
- Create: `configs/layers/base/layer2_sector.yaml`
- Create: `configs/layers/base/layer3_superinvestors.yaml`
- Create: `configs/layers/base/layer4_decision.yaml`
- Test: `tests/layers/test_layer1_macro.py`

- [ ] **Step 1: Write the failing test** asserting loader can read base files and returns `version`, `agents`, and `weights` keys.
- [ ] **Step 2: Run test to verify it fails**.
  - Run: `pytest tests/layers/test_layer1_macro.py::test_load_layer_config_from_base -v`
  - Expected: FAIL due to missing loader/files.
- [ ] **Step 3: Write minimal implementation** of `load_layer_config(layer_name, profile='base')` with path safety and clear errors.
- [ ] **Step 4: Run test to verify it passes**.
  - Run: `pytest tests/layers/test_layer1_macro.py::test_load_layer_config_from_base -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/layers/config_loader.py configs/layers/base/*.yaml tests/layers/test_layer1_macro.py`
  - `git commit -m "feat(config): add layer config loader and base layer YAMLs"`

---

## Chunk 2: Runtime four-layer decision path

### Task 3: Implement Layer 1 macro agents

**Files:**
- Create: `app/layers/layer1_macro.py`
- Modify: `app/signal_orchestrator.py`
- Test: `tests/layers/test_layer1_macro.py`

- [ ] **Step 1: Write failing tests** for ten macro agents returning deterministic outputs for deterministic fixtures.
- [ ] **Step 2: Run tests to verify failure**.
  - Run: `pytest tests/layers/test_layer1_macro.py -v`
  - Expected: FAIL due to missing `MacroLayer`.
- [ ] **Step 3: Implement `MacroLayer.evaluate()`** reading config weights and current market context.
- [ ] **Step 4: Re-run tests to verify pass**.
  - Run: `pytest tests/layers/test_layer1_macro.py -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/layers/layer1_macro.py app/signal_orchestrator.py tests/layers/test_layer1_macro.py`
  - `git commit -m "feat(layer1): add macro layer evaluation"`

### Task 4: Implement Layer 2 sector desks (ETF/sector-first)

**Files:**
- Create: `app/layers/layer2_sector.py`
- Modify: `app/universe.py`
- Test: `tests/layers/test_layer2_sector.py`

- [ ] **Step 1: Write failing tests** for sector desk ranking and ETF preference over single-stock outputs.
- [ ] **Step 2: Run tests to verify failure**.
  - Run: `pytest tests/layers/test_layer2_sector.py -v`
  - Expected: FAIL due to missing `SectorLayer`.
- [ ] **Step 3: Implement `SectorLayer.evaluate()`** mapping macro context to sector-scored ETF candidates.
- [ ] **Step 4: Re-run tests to verify pass**.
  - Run: `pytest tests/layers/test_layer2_sector.py -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/layers/layer2_sector.py app/universe.py tests/layers/test_layer2_sector.py`
  - `git commit -m "feat(layer2): add sector desk ETF-first ranking"`

### Task 5: Implement Layer 3 superinvestor reweighting

**Files:**
- Create: `app/layers/layer3_superinvestors.py`
- Test: `tests/layers/test_layer3_superinvestors.py`

- [ ] **Step 1: Write failing tests** asserting four investor filters reweight sector candidates and keep provenance metadata.
- [ ] **Step 2: Run tests to verify failure**.
  - Run: `pytest tests/layers/test_layer3_superinvestors.py -v`
  - Expected: FAIL due to missing `SuperinvestorLayer`.
- [ ] **Step 3: Implement `SuperinvestorLayer.evaluate()`** with bounded weight adjustments.
- [ ] **Step 4: Re-run tests to verify pass**.
  - Run: `pytest tests/layers/test_layer3_superinvestors.py -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/layers/layer3_superinvestors.py tests/layers/test_layer3_superinvestors.py`
  - `git commit -m "feat(layer3): add superinvestor reweighting layer"`

### Task 6: Implement Layer 4 decision aggregation

**Files:**
- Create: `app/layers/layer4_decision.py`
- Modify: `app/signal_orchestrator.py`
- Test: `tests/layers/test_layer4_decision.py`

- [ ] **Step 1: Write failing tests** for final decision aggregation and proposal confidence thresholds.
- [ ] **Step 2: Run tests to verify failure**.
  - Run: `pytest tests/layers/test_layer4_decision.py -v`
  - Expected: FAIL due to missing `DecisionLayer`.
- [ ] **Step 3: Implement `DecisionLayer.evaluate()`** that produces final proposal set with rationale fields.
- [ ] **Step 4: Re-run tests to verify pass**.
  - Run: `pytest tests/layers/test_layer4_decision.py -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/layers/layer4_decision.py app/signal_orchestrator.py tests/layers/test_layer4_decision.py`
  - `git commit -m "feat(layer4): add final decision aggregation layer"`

### Task 7: Wire four layers into daily runtime pipeline

**Files:**
- Modify: `app/signal_orchestrator.py`
- Modify: `app/pipeline/daily_runner.py`
- Test: `tests/integration/test_layered_pipeline.py`

- [ ] **Step 1: Write failing integration test** asserting all four layers run and output is passed to risk/approval stages.
- [ ] **Step 2: Run tests to verify failure**.
  - Run: `pytest tests/integration/test_layered_pipeline.py -v`
  - Expected: FAIL because current pipeline logs placeholders.
- [ ] **Step 3: Implement orchestration wiring** and replace placeholder stage branches.
- [ ] **Step 4: Re-run tests to verify pass**.
  - Run: `pytest tests/integration/test_layered_pipeline.py -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/signal_orchestrator.py app/pipeline/daily_runner.py tests/integration/test_layered_pipeline.py`
  - `git commit -m "feat(pipeline): wire layered decision runtime into daily runner"`

---

## Chunk 3: Shadow-mode autoresearch loop

### Task 8: Add decision memory persistence

**Files:**
- Create: `app/autoresearch/decision_memory.py`
- Modify: `app/schemas.py`
- Modify: `app/pipeline/daily_runner.py`
- Test: `tests/autoresearch/test_decision_memory.py`

- [ ] **Step 1: Write failing tests** for append-only write/read of run records and realized outcomes.
- [ ] **Step 2: Run tests to verify failure**.
  - Run: `pytest tests/autoresearch/test_decision_memory.py -v`
  - Expected: FAIL due to missing `DecisionMemory`.
- [ ] **Step 3: Implement `DecisionMemory`** with JSONL persistence and schema validation.
- [ ] **Step 4: Re-run tests to verify pass**.
  - Run: `pytest tests/autoresearch/test_decision_memory.py -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/autoresearch/decision_memory.py app/schemas.py app/pipeline/daily_runner.py tests/autoresearch/test_decision_memory.py`
  - `git commit -m "feat(autoresearch): add append-only decision memory"`

### Task 9: Add scorecard and versioning metadata

**Files:**
- Create: `app/autoresearch/scorecard.py`
- Create: `app/autoresearch/versioning.py`
- Test: `tests/autoresearch/test_scorecard.py`

- [ ] **Step 1: Write failing tests** for per-agent hit rate, mean return, and config version tagging.
- [ ] **Step 2: Run tests to verify failure**.
  - Run: `pytest tests/autoresearch/test_scorecard.py -v`
  - Expected: FAIL due to missing `ScorecardEngine`.
- [ ] **Step 3: Implement `ScorecardEngine.score()` and version helper functions**.
- [ ] **Step 4: Re-run tests to verify pass**.
  - Run: `pytest tests/autoresearch/test_scorecard.py -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/autoresearch/scorecard.py app/autoresearch/versioning.py tests/autoresearch/test_scorecard.py`
  - `git commit -m "feat(autoresearch): add scorecard metrics and config versioning"`

### Task 10: Add bounded policy updater (single-change mutation)

**Files:**
- Create: `app/autoresearch/policy_updater.py`
- Test: `tests/autoresearch/test_policy_updater.py`

- [ ] **Step 1: Write failing tests** ensuring only one parameter mutates per cycle and all safety bounds are enforced.
- [ ] **Step 2: Run tests to verify failure**.
  - Run: `pytest tests/autoresearch/test_policy_updater.py -v`
  - Expected: FAIL due to missing `PolicyUpdater`.
- [ ] **Step 3: Implement `PolicyUpdater.propose()`** with explicit min/max clamps and audit metadata.
- [ ] **Step 4: Re-run tests to verify pass**.
  - Run: `pytest tests/autoresearch/test_policy_updater.py -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/autoresearch/policy_updater.py tests/autoresearch/test_policy_updater.py`
  - `git commit -m "feat(autoresearch): add bounded single-change policy updater"`

### Task 11: Add replay evaluator and keep-or-revert decision

**Files:**
- Create: `app/autoresearch/replay_evaluator.py`
- Create: `fixtures/replay/day_01.yaml`
- Create: `fixtures/replay/day_02.yaml`
- Create: `fixtures/replay/outcomes_01.yaml`
- Modify: `app/test_harness.py`
- Test: `tests/autoresearch/test_replay_evaluator.py`

- [ ] **Step 1: Write failing tests** for candidate vs baseline replay comparison and deterministic keep/revert verdict.
- [ ] **Step 2: Run tests to verify failure**.
  - Run: `pytest tests/autoresearch/test_replay_evaluator.py -v`
  - Expected: FAIL due to missing `ReplayEvaluator`.
- [ ] **Step 3: Implement `ReplayEvaluator.compare()`** using fixtures and `app/test_harness.py` integration.
- [ ] **Step 4: Re-run tests to verify pass**.
  - Run: `pytest tests/autoresearch/test_replay_evaluator.py -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/autoresearch/replay_evaluator.py app/test_harness.py fixtures/replay/*.yaml tests/autoresearch/test_replay_evaluator.py`
  - `git commit -m "feat(replay): add keep-or-revert evaluator for candidate configs"`

### Task 12: Wire shadow promotion flow into daily runner

**Files:**
- Modify: `app/pipeline/daily_runner.py`
- Modify: `app/signal_orchestrator.py`
- Create: `configs/layers/promoted/README.md`
- Test: `tests/integration/test_shadow_mode_promotion.py`

- [ ] **Step 1: Write failing integration tests** for post-close sequence: memory -> scorecard -> mutation -> replay -> promote/revert.
- [ ] **Step 2: Run tests to verify failure**.
  - Run: `pytest tests/integration/test_shadow_mode_promotion.py -v`
  - Expected: FAIL because flow is not implemented.
- [ ] **Step 3: Implement offline shadow cycle wiring** with explicit paper-only guardrails and promotion write path under `configs/layers/promoted/`.
- [ ] **Step 4: Re-run tests to verify pass**.
  - Run: `pytest tests/integration/test_shadow_mode_promotion.py -v`
  - Expected: PASS.
- [ ] **Step 5: Commit**.
  - `git add app/pipeline/daily_runner.py app/signal_orchestrator.py configs/layers/promoted/README.md tests/integration/test_shadow_mode_promotion.py`
  - `git commit -m "feat(shadow): add replay-gated config promotion workflow"`

---

## Chunk 4: Safety docs and full verification

### Task 13: Update operational runbook for layered autoresearch

**Files:**
- Modify: `docs/RUNBOOK.md`

- [ ] **Step 1: Add runbook sections** for shadow-mode cadence, replay gates, and rollback procedures.
- [ ] **Step 2: Add command examples** for runtime and post-close learning stages.
- [ ] **Step 3: Verify docs references** match actual files and commands.
- [ ] **Step 4: Commit**.
  - `git add docs/RUNBOOK.md`
  - `git commit -m "docs: add layered autoresearch and replay promotion runbook"`

### Task 14: Full test and quality gate

**Files:**
- Modify: as needed from fixes discovered during verification

- [ ] **Step 1: Run focused suites**.
  - `pytest tests/layers -v`
  - `pytest tests/autoresearch -v`
  - `pytest tests/integration -v`
- [ ] **Step 2: Run full suite**.
  - `pytest -v`
- [ ] **Step 3: Run any existing project lint/type checks** defined in `pyproject.toml`.
- [ ] **Step 4: Fix failures and re-run until green**.
- [ ] **Step 5: Final commit for verification fixes**.
  - `git add -A`
  - `git commit -m "test: make layered autoresearch pipeline pass full verification"`

---

## Execution notes

- Keep mutation surface limited to layer config values; do not mutate risk hard stops, approval requirements, or live-trading gates.
- Default runtime remains paper-first and human-approved.
- Every mutation cycle must emit an audit record (what changed, why, replay result, promotion/revert verdict).
- If replay fixtures are stale or incomplete, force `revert` and leave promoted config untouched.

Plan complete and saved to `docs/superpowers/plans/2026-03-13-atlas-layered-autoresearch.md`. Ready to execute.
