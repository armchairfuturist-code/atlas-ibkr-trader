# IBKR Paper ETF/Sector Margin Planner Implementation Plan

## TL;DR

> **Quick Summary**: Build a paper-first, human-approved trading decision system that uses ATLAS-inspired multi-agent research ideas but enforces strict pre-trade risk checks for ETF/sector margin workflows.
>
> **Deliverables**:
> - Deterministic research-to-order-intent pipeline (paper only)
> - Hard risk engine (1.25x gross max, 12.5% position, 30% sector, 2.5% daily stop)
> - Human approval gate and IBKR paper adapter with full audit logs
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 4 waves + final verification wave
> **Critical Path**: Task 2 -> Task 8 -> Task 10 -> Task 13 -> Task 15 -> Final Wave

---

## Context

### Original Request
Use `https://github.com/chrisworsey55/atlas-gic` (Karpathy autoresearch style) to help make trades for a margin account, with focus on ETFs/sectors over individual stocks.

### Interview Summary
**Key Discussions**:
- Execution target: IBKR paper account first.
- Universe: include unlevered + leveraged + inverse ETFs, with slight priority to unlevered products.
- Order flow: human approval required before any paper order placement.
- Risk profile: max gross leverage 1.25x, max position 12.5%, max sector concentration 30%, daily loss stop 2.5%.
- Horizon: multi-day swing.
- Testing: TDD required + agent-executed QA scenarios required.

**Research Findings**:
- Public `atlas-gic` repository is mostly architecture docs/prompts/results, not complete executable trading source code.
- `src/README.md` explicitly states implementation details are not included.
- `results/summary.json` shows negative total return in sample output, reinforcing need for explicit orchestration and risk controls.

### Reference Baseline
- Clone/read-only reference at: `C:\Users\Administrator\atlas-gic`
- Reference commit pin: `9d6310432351bd94d6709c4e30411e373029e049`
- Any reference path prefixed with `atlas-gic/` means: `C:\Users\Administrator\atlas-gic\...` at the pinned commit.

### Metis Review
**Identified Gaps** (addressed via substitute deep review):
- Need explicit effective exposure math for leveraged/inverse ETFs.
- Need non-circumventable paper-only and human-approval gates.
- Need deterministic replay, stale-data fail-closed behavior, and edge-case tests.

---

### IBKR Setup Checklist

Before running the pipeline with live paper trading, complete these steps:

1. **Configure TWS/IB Gateway in Paper Mode**
   - Open TWS → Settings → API → **Paper Trading** checkbox enabled
   - Or launch IB Gateway with paper credentials (separate login from live)
   - Default socket port: `7497` (paper) vs `7496` (live)
   - Ensure "Allow connections from localhost only" for security

2. **Verify Paper Account**
   - Login to Account Management with paper credentials
   - Confirm account starts with `DU` (e.g., `DU123456`)
   - Note: Paper account has separate cash/positions from live

3. **API Permissions**
   - TWS → Settings → API → **Enable ActiveX and Socket Clients**
   - Check "Read-Only API" is OFF for order placement
   - Firewall: allow `127.0.0.1` on port `7497`

4. **Environment Variables** (for the app)
   ```bash
   export IBKR_PAPER_HOST=127.0.0.1
   export IBKR_PAPER_PORT=7497
   export IBKR_CLIENT_ID=1  # Unique per connection
   ```

5. **Test Connection** (Task 10 will validate)
   - Run connection test: should return paper account ID
   - Verify buying power shows non-zero

---

## Work Objectives

### Core Objective
Deliver a production-style paper-trading decision-support system that transforms ATLAS-inspired research signals into risk-checked, human-approved ETF/sector order intents for IBKR paper execution.

### Concrete Deliverables
- A runnable pipeline that ingests market/context data, computes ETF/sector signals, applies risk constraints, and emits approvable order intents.
- A risk engine enforcing selected caps and daily stop with leveraged/inverse ETF effective exposure handling.
- A human approval workflow and paper-only IBKR adapter that blocks live execution.
- Full automated tests (TDD) and agent-executed QA evidence.

### Definition of Done
- [ ] Full daily pipeline run succeeds in paper mode and generates deterministic outputs from fixed fixtures.
- [ ] Risk violations are blocked with machine-readable reject codes.
- [ ] No order can be submitted without explicit human approval artifact.
- [ ] Live-mode account execution is blocked by policy guardrails.

### Must Have
- Hard paper-only lock and human-approval gate.
- Deterministic behavior under fixture replay.
- Fail-closed no-trade behavior on stale/missing critical data.
- ETF/sector focus with leverage-aware risk accounting.
- Default trading domain: US-listed ETFs during regular market hours (extend only via explicit future scope change).

### Must NOT Have (Guardrails)
- No autonomous live-trading path in this phase.
- No bypasses for risk checks or approval checks.
- No scope expansion into full OMS, options engine, or multi-asset infra.
- No dependence on proprietary ATLAS prompt files unavailable in public repo.

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION FOR VERIFICATION** — all acceptance checks are executable by agent commands/tools.

### Test Decision
- **Infrastructure exists**: NO (from public repo baseline)
- **Automated tests**: TDD
- **Framework**: `pytest` (+ optional `pytest-asyncio`)
- **If TDD**: each task follows RED -> GREEN -> REFACTOR

### QA Policy
Evidence path convention: `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`

- **Frontend/UI**: N/A for core scope (CLI/API-first)
- **CLI/TUI**: `interactive_bash` (tmux) for workflow runs and manual approval flow checks
- **API/Backend**: Bash (`python -m`, `curl` if HTTP wrapper exists)
- **Library/Module**: Bash (`pytest`, Python module invocations)

Every task below includes at least one happy-path and one negative/error QA scenario.

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Start Immediately - foundations, 6 tasks):
- Task 1: Python project scaffold and dependency baseline
- Task 2: Config model + paper-only environment lock
- Task 3: ETF universe catalog + leverage metadata + sector taxonomy
- Task 4: Market data provider abstraction + adapters
- Task 5: Decision, risk, and audit event schemas
- Task 6: Test harness + fixtures + deterministic snapshot utilities

Wave 2 (After Wave 1 - core engine, 6 tasks):
- Task 7: ATLAS-inspired layered signal orchestrator
- Task 8: Risk engine (effective exposure, caps, daily stop, liquidity/spread checks)
- Task 9: Human approval gate service for proposed intents (tokened approval + replay protection)
- Task 10: IBKR paper adapter + pre-trade broker checks
- Task 11: Recommendation-to-proposed-intent translator
- Task 12: Stale/missing data fail-closed and no-trade controller

Wave 3 (After Wave 2 - integration, 4 tasks):
- Task 13: End-to-end daily pipeline runner (CLI or minimal API)
- Task 14: Audit/report output pack (decisions, risk verdicts, approvals)
- Task 15: Integration test suite for boundary + negative scenarios
- Task 16: Operational runbook and safety checklist docs

Wave 4 (After Wave 3 - release hardening, 3 tasks):
- Task 17: Paper execution smoke tests in IBKR sandbox conditions
- Task 18: Regression replay against fixed market snapshots
- Task 19: Packaging and environment profile hardening (dev/paper)

Wave FINAL (After ALL tasks - independent review, 4 parallel):
- Task F1: Plan compliance audit (oracle-equivalent reviewer)
- Task F2: Code quality review
- Task F3: Real QA execution of all scenarios + evidence completeness
- Task F4: Scope fidelity check (no live-trading creep)

Critical Path: 2 -> 8 -> 10 -> 13 -> 15 -> F1/F4
Parallel Speedup: ~60-70% over sequential
Max Concurrent: 6

### Dependency Matrix

- Task 1: blocked_by none; blocks 6,7,13,19
- Task 2: blocked_by none; blocks 8,10,12,13,17,19
- Task 3: blocked_by none; blocks 7,8,11,15
- Task 4: blocked_by none; blocks 7,10,12,13,17
- Task 5: blocked_by none; blocks 7,8,9,11,14,15
- Task 6: blocked_by 1; blocks 15,18
- Task 7: blocked_by 1,3,4,5; blocks 11,13,14,15
- Task 8: blocked_by 2,3,5; blocks 10,11,12,13,15,17
- Task 9: blocked_by 5,11; blocks 10,13,14,15
- Task 10: blocked_by 2,4,8,9; blocks 13,17,19
- Task 11: blocked_by 3,5,7,8; blocks 9,13,14,15
- Task 12: blocked_by 2,4,8; blocks 13,15,17
- Task 13: blocked_by 1,2,4,7,8,9,10,11,12; blocks 14,15,17,18
- Task 14: blocked_by 5,7,9,11,13; blocks 16,F1,F3,F4
- Task 15: blocked_by 3,5,6,7,8,9,11,12,13; blocks 17,18,F2,F3
- Task 16: blocked_by 14; blocks F1,F4
- Task 17: blocked_by 2,4,8,10,12,13,15; blocks F3
- Task 18: blocked_by 6,13,15; blocks F2,F3
- Task 19: blocked_by 1,2,10; blocks F2,F4

### Agent Dispatch Summary

- Wave 1: T1 `quick`, T2 `unspecified-high`, T3 `quick`, T4 `unspecified-high`, T5 `quick`, T6 `quick`
- Wave 2: T7 `deep`, T8 `deep`, T9 `quick`, T10 `unspecified-high`, T11 `quick`, T12 `deep`
- Wave 3: T13 `deep`, T14 `writing`, T15 `deep`, T16 `writing`
- Wave 4: T17 `unspecified-high`, T18 `deep`, T19 `quick`
- Final: F1 `deep`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## TODOs

- [ ] 1. Scaffold Python project and runtime baseline

  **What to do**:
  - Create minimal project layout (`app/`, `tests/`, `fixtures/`, `scripts/`) and dependency manifest for pipeline work.
  - Add command entrypoint for daily paper run.
  - Start RED test for project boot command, then GREEN implementation.

  **Must NOT do**:
  - Do not add live trading credentials or live broker endpoints.

  **Recommended Agent Profile**:
  - **Category**: `quick` (bootstrap and low-ambiguity setup)
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `react-native-best-practices` (no RN scope)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with 2,3,4,5)
  - **Blocks**: 6,7,13,19
  - **Blocked By**: None

  **References**:
  - `atlas-gic/src/README.md` - expected source module boundaries and data flow intent.
  - `atlas-gic/architecture/overview.md` - orchestration pattern to mirror in file structure.

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_bootstrap.py -q` passes.
  - [ ] `python -m app.pipeline.run_daily --help` returns usage without error.

  **QA Scenarios**:
  ```
  Scenario: Bootstrap command works
    Tool: Bash
    Preconditions: Fresh venv with dependencies installed
    Steps:
      1. Run `python -m app.pipeline.run_daily --help`
      2. Capture exit code
      3. Assert output contains `--mode` and `--fixture`
    Expected Result: Exit code 0 and help text present
    Evidence: .sisyphus/evidence/task-1-help.txt

  Scenario: Missing module fails clearly
    Tool: Bash
    Preconditions: Intentionally run wrong module path
    Steps:
      1. Run `python -m app.pipeline.missing`
      2. Assert non-zero exit code
      3. Assert error contains `No module named`
    Expected Result: Controlled Python import error
    Evidence: .sisyphus/evidence/task-1-missing-module-error.txt
  ```

  **Commit**: YES
  - Message: `feat(core): scaffold pipeline runtime`

- [ ] 2. Implement config model and paper-only execution lock

  **What to do**:
  - Define config schema for account mode, leverage caps, concentration caps, and daily stop.
  - Enforce fail-closed rule: if mode is not `paper`, execution stage halts.
  - TDD boundary tests for invalid config and unsafe mode transitions.

  **Must NOT do**:
  - Do not permit fallback to live mode.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `agent-browser` (no browser interaction)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: 8,10,12,13,17,19
  - **Blocked By**: None

  **References**:
  - `atlas-gic/prompts/examples/cio.md` - source for risk-control vocabulary to map into explicit config fields.
  - FINRA Rule 4210 (official): `https://www.finra.org/rules-guidance/rulebooks/finra-rules/4210` - baseline margin-aware constraints.

  **Acceptance Criteria**:
  - [ ] Invalid config fails schema validation with explicit errors.
  - [ ] Any `mode != paper` blocks order submission path.

  **QA Scenarios**:
  ```
  Scenario: Paper mode accepted
    Tool: Bash
    Preconditions: Config file with `mode: paper`
    Steps:
      1. Run `python -m app.tools.validate_config --config fixtures/config.paper.yaml`
      2. Assert validation success
      3. Assert runtime shows `paper lock enabled`
    Expected Result: Config accepted and lock state confirmed
    Evidence: .sisyphus/evidence/task-2-paper-ok.txt

  Scenario: Live mode blocked
    Tool: Bash
    Preconditions: Config file with `mode: live`
    Steps:
      1. Run `python -m app.tools.validate_config --config fixtures/config.live.yaml`
      2. Assert non-zero exit code
      3. Assert message contains `live mode blocked`
    Expected Result: Fail-closed block
    Evidence: .sisyphus/evidence/task-2-live-blocked.txt
  ```

  **Commit**: YES
  - Message: `feat(safety): add paper-only config guardrail`

- [ ] 3. Build ETF universe catalog with leverage and sector metadata

  **What to do**:
  - Create canonical universe file including unlevered, leveraged, and inverse ETFs.
  - Include metadata fields: leverage factor, inverse flag, primary sector, liquidity thresholds.
  - Add tests for schema validity and duplicate symbol rejection.

  **Must NOT do**:
  - Do not allow assets outside ETF universe in phase 1.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `webapp-testing` (not web scope)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: 7,8,11,15
  - **Blocked By**: None

  **References**:
  - `atlas-gic/architecture/layers.md` - sector desk concept and sector-level signal context.
  - `atlas-gic/prompts/examples/sector_desk.md` - sector ETF input expectations.

  **Acceptance Criteria**:
  - [ ] Universe loader returns normalized symbols and metadata.
  - [ ] Duplicate or malformed entry fails with deterministic error.

  **QA Scenarios**:
  ```
  Scenario: Universe loads successfully
    Tool: Bash
    Preconditions: Valid universe file
    Steps:
      1. Run `python -m app.tools.check_universe --file fixtures/universe.valid.yaml`
      2. Assert output count > 0
      3. Assert at least one unlevered and one leveraged ETF entry exists
    Expected Result: Valid mixed universe loaded
    Evidence: .sisyphus/evidence/task-3-universe-ok.txt

  Scenario: Non-ETF symbol rejected
    Tool: Bash
    Preconditions: Add invalid symbol type row to test fixture
    Steps:
      1. Run loader against invalid fixture
      2. Assert non-zero exit code
      3. Assert error includes `unsupported asset type`
    Expected Result: Invalid assets blocked
    Evidence: .sisyphus/evidence/task-3-invalid-asset-error.txt
  ```

  **Commit**: YES
  - Message: `feat(universe): add ETF sector/leverage catalog`

- [ ] 4. Create market data abstraction and adapter stubs

  **What to do**:
  - Define provider interface for quotes, OHLCV, and freshness timestamps.
  - Add adapter stubs for configured sources (FMP/Finnhub/Polygon style contracts).
  - Set default startup provider to `fixture` mode (`fixtures/day_ok.json`) until explicit API keys are configured.
  - Write RED tests for stale/missing data flags.

  **Must NOT do**:
  - Do not silently backfill critical missing market fields.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `ui-ux-pro-max` (non-UI)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: 7,10,12,13,17
  - **Blocked By**: None

  **References**:
  - `atlas-gic/README.md` - declared data sources and pipeline assumptions.
  - `atlas-gic/architecture/overview.md` - data refresh and layer timing model.

  **Acceptance Criteria**:
  - [ ] Interface contract tests pass for normal and stale data cases.
  - [ ] Freshness metadata is available to downstream risk/no-trade checks.

  **QA Scenarios**:
  ```
  Scenario: Fresh quote path
    Tool: Bash
    Preconditions: Fixture provider returns timestamp within freshness threshold
    Steps:
      1. Run `pytest tests/data/test_provider_contract.py::test_fresh_quote_path -q`
      2. Assert latest quote marked fresh
      3. Assert downstream call receives freshness=true
    Expected Result: Fresh data accepted
    Evidence: .sisyphus/evidence/task-4-fresh-data.txt

  Scenario: Stale quote path
    Tool: Bash
    Preconditions: Fixture provider timestamp older than threshold
    Steps:
      1. Run stale-data test
      2. Assert stale flag true
      3. Assert downstream no-trade trigger occurs
    Expected Result: Stale data blocks trading path
    Evidence: .sisyphus/evidence/task-4-stale-block.txt
  ```

  **Commit**: YES
  - Message: `feat(data): add provider abstraction and freshness checks`

- [ ] 5. Define decision, risk, and audit schemas

  **What to do**:
  - Create strict schemas for signal, recommendation, risk verdict, approval record, and order intent.
  - Add machine-readable reject codes for every risk block reason.
  - TDD schema serialization/deserialization and versioning tests.

  **Must NOT do**:
  - Do not use free-form objects for core pipeline interfaces.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `agent-browser` (irrelevant)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: 7,8,9,11,14,15
  - **Blocked By**: None

  **References**:
  - `atlas-gic/architecture/layers.md` - expected cross-layer JSON communication model.
  - `atlas-gic/prompts/examples/cio.md` - final action/output schema inspiration.

  **Acceptance Criteria**:
  - [ ] Schema tests enforce required fields and reject unknown critical fields.
  - [ ] Reject code enum fully mapped to risk engine checks.

  **QA Scenarios**:
  ```
  Scenario: Valid order intent serializes
    Tool: Bash
    Preconditions: Construct valid in-memory intent fixture
    Steps:
      1. Run schema validation test
      2. Assert serialization succeeds
      3. Assert round-trip equality
    Expected Result: Stable schema round-trip
    Evidence: .sisyphus/evidence/task-5-schema-roundtrip.txt

  Scenario: Missing reject code fails
    Tool: Bash
    Preconditions: Invalid risk verdict fixture without reject code
    Steps:
      1. Run `pytest tests/schema/test_risk_schema.py::test_reject_code_required -q`
      2. Assert failure
      3. Assert error names missing `reject_code`
    Expected Result: Invalid structure rejected
    Evidence: .sisyphus/evidence/task-5-schema-error.txt
  ```

  **Commit**: YES
  - Message: `feat(schema): define decision-risk-audit contracts`

- [ ] 6. Set up TDD harness and deterministic fixtures

  **What to do**:
  - Configure pytest + fixture strategy for deterministic daily snapshots.
  - Add helpers for seeded randomness elimination and frozen timestamps.
  - Ensure baseline CI test command exists.

  **Must NOT do**:
  - Do not leave time-dependent tests nondeterministic.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `webapp-testing` (no browser)

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (after Task 1)
  - **Blocks**: 15,18
  - **Blocked By**: 1

  **References**:
  - `atlas-gic/results/autoresearch_log.json` - realistic event-style fixtures for tests.
  - `atlas-gic/results/summary.json` - summary metrics fixture shape.

  **Acceptance Criteria**:
  - [ ] `pytest -q` is reproducible across repeated runs.
  - [ ] Fixture snapshot tests remain stable across timezone differences.

  **QA Scenarios**:
  ```
  Scenario: Reproducible test run
    Tool: Bash
    Preconditions: Clean working tree
    Steps:
      1. Run `pytest -q` twice
      2. Compare pass/fail counts
      3. Assert identical outcomes
    Expected Result: Deterministic test results
    Evidence: .sisyphus/evidence/task-6-determinism.txt

  Scenario: Unfrozen time test fails
    Tool: Bash
    Preconditions: Use scripted fixture toggle `fixtures/time_unfrozen.json`
    Steps:
      1. Run `pytest tests/core/test_time_controls.py::test_unfrozen_clock_rejected -q`
      2. Assert failure indicates time nondeterminism
      3. Run `pytest tests/core/test_time_controls.py::test_frozen_clock_passes -q`
    Expected Result: Harness catches nondeterministic tests
    Evidence: .sisyphus/evidence/task-6-time-freeze-error.txt
  ```

  **Commit**: YES
  - Message: `test(core): establish deterministic TDD harness`

- [ ] 7. Implement layered signal orchestrator (ATLAS-inspired)

  **What to do**:
  - Build modular signal stages: macro context -> sector preference -> committee synthesis.
  - Use ETF/sector outputs as primary recommendation surface.
  - Add RED tests for deterministic ranking and tie-breaking.

  **Must NOT do**:
  - Do not depend on proprietary prompt internals from private ATLAS assets.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `remotion-best-practices` (irrelevant)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with 8,9,10,11,12)
  - **Blocks**: 11,13,14,15
  - **Blocked By**: 1,3,4,5

  **References**:
  - `atlas-gic/architecture/overview.md` - four-layer idea flow to emulate.
  - `atlas-gic/architecture/layers.md` - per-layer outputs and aggregation hints.

  **Acceptance Criteria**:
  - [ ] Given fixed fixtures, top-N recommendations are deterministic.
  - [ ] Output strictly uses schema from Task 5.

  **QA Scenarios**:
  ```
  Scenario: Deterministic ranking
    Tool: Bash
    Preconditions: Fixed market snapshot fixture
    Steps:
      1. Run orchestrator twice with same fixture
      2. Compare ordered recommendation IDs
      3. Assert exact match
    Expected Result: Stable ordered output
    Evidence: .sisyphus/evidence/task-7-deterministic-ranking.txt

  Scenario: Unknown sector input rejected
    Tool: Bash
    Preconditions: Fixture includes unknown sector label
    Steps:
      1. Execute orchestrator test
      2. Assert error code for invalid sector mapping
      3. Verify no recommendation emitted
    Expected Result: Fail-closed invalid sector handling
    Evidence: .sisyphus/evidence/task-7-invalid-sector-error.txt
  ```

  **Commit**: YES
  - Message: `feat(signal): add layered ETF-sector orchestrator`

- [ ] 8. Build risk engine with effective exposure accounting

  **What to do**:
  - Enforce hard limits: 1.25x gross, 12.5% position, 30% sector, 2.5% daily loss stop.
  - Compute effective exposure using ETF leverage multiplier and inverse semantics.
  - Add liquidity/spread prechecks and reject codes.

  **Must NOT do**:
  - Do not evaluate leveraged ETFs by raw notional only.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `ui-ux-pro-max` (not UI)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: 10,11,12,13,15,17
  - **Blocked By**: 2,3,5

  **References**:
  - FINRA 4210: `https://www.finra.org/rules-guidance/rulebooks/finra-rules/4210` - margin governance baseline.
  - FINRA leveraged ETF margin notice: `https://www.finra.org/rules-guidance/notices/09-53` - leverage-aware margin caution.
  - `atlas-gic/prompts/examples/cio.md` - portfolio-level risk controls pattern.

  **Acceptance Criteria**:
  - [ ] Boundary tests pass at and just beyond each hard threshold.
  - [ ] Reject reasons map to deterministic machine-readable codes.

  **QA Scenarios**:
  ```
  Scenario: Risk-compliant proposal passes
    Tool: Bash
    Preconditions: Proposal under all configured limits
    Steps:
      1. Run risk engine evaluation
      2. Assert verdict `PASS`
      3. Assert no reject codes returned
    Expected Result: Proposal approved by risk layer
    Evidence: .sisyphus/evidence/task-8-risk-pass.txt

  Scenario: Gross leverage breach blocked
    Tool: Bash
    Preconditions: Proposal pushes effective gross > 1.25
    Steps:
      1. Evaluate proposal
      2. Assert verdict `REJECT`
      3. Assert reject code `GROSS_LEVERAGE_BREACH`
    Expected Result: Hard block with explicit code
    Evidence: .sisyphus/evidence/task-8-gross-breach.txt
  ```

  **Commit**: YES
  - Message: `feat(risk): enforce hard caps and leverage-aware exposure`

- [ ] 9. Implement human approval gate with replay protection

  **What to do**:
  - Create proposed-intent queue and approval token flow.
  - Require approval record (timestamp, approver id, rationale) before execution.
  - Add anti-replay tests to prevent duplicate submissions.

  **Must NOT do**:
  - Do not allow implicit approvals.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `agent-browser` (CLI flow)

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Task 11)
  - **Blocks**: 10,13,14,15
  - **Blocked By**: 5,11

  **References**:
  - `atlas-gic/architecture/autoresearch.md` - auditability and git-trace mindset for mutation control.

  **Acceptance Criteria**:
  - [ ] Unapproved proposed intent cannot pass execution stage.
  - [ ] Replay of consumed token is rejected.

  **QA Scenarios**:
  ```
  Scenario: Approved intent executes path
    Tool: Bash
    Preconditions: Proposed intent with valid approval token
    Steps:
      1. Submit approval
      2. Trigger execution preflight
      3. Assert state transitions to `approved` then `submitted`
    Expected Result: Approved intent allowed
    Evidence: .sisyphus/evidence/task-9-approval-pass.txt

  Scenario: Missing approval blocked
    Tool: Bash
    Preconditions: Pending intent without approval
    Steps:
      1. Trigger execution preflight
      2. Assert blocked
      3. Assert reject code `APPROVAL_REQUIRED`
    Expected Result: Strict approval gate enforcement
    Evidence: .sisyphus/evidence/task-9-approval-required.txt
  ```

  **Commit**: YES
  - Message: `feat(flow): add mandatory human approval gate`

- [ ] 10. Implement IBKR paper adapter with pre-trade checks

  **What to do**:
  - Build adapter for IBKR paper account connectivity and order submission simulation.
  - Add pre-trade checks for account mode, buying power, and broker rejection mapping.
  - Add integration tests using mocks/sandbox mode.

  **Must NOT do**:
  - Do not include live account submission path in phase 1.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `webapp-testing` (non-web)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: 13,17,19
  - **Blocked By**: 2,4,8,9

  **References**:
  - IBKR margin context: `https://www.ibkrguides.com/kb/article-1124.htm` - leveraged ETF margin sensitivity.
  - `atlas-gic/README.md` - autonomous execution concept to adapt safely to paper-only.

  **Acceptance Criteria**:
  - [ ] Adapter rejects any non-paper account mode.
  - [ ] Broker-level rejection codes are normalized into internal error schema.

  **QA Scenarios**:
  ```
  Scenario: Paper submission accepted
    Tool: Bash
    Preconditions: Mock/sandbox IBKR in paper mode, approved intent
    Steps:
      1. Submit intent via adapter
      2. Assert broker ack simulated/returned
      3. Assert internal status `submitted_paper`
    Expected Result: Paper route succeeds
    Evidence: .sisyphus/evidence/task-10-paper-submit.txt

  Scenario: Live account blocked at adapter
    Tool: Bash
    Preconditions: Adapter initialized with live mode flag
    Steps:
      1. Attempt submit
      2. Assert hard failure
      3. Assert error `LIVE_MODE_FORBIDDEN`
    Expected Result: Live path impossible
    Evidence: .sisyphus/evidence/task-10-live-forbidden.txt
  ```

  **Commit**: YES
  - Message: `feat(exec): add ibkr paper adapter and safety checks`

- [ ] 11. Translate recommendations into order intents

  **What to do**:
  - Convert ranked recommendations into sized proposed intents after risk verdicts and before approval.
  - Include sector-priority logic favoring unlevered ETFs when equivalent signal strength exists.
  - Add tests for sizing math and tie-break rules.

  **Must NOT do**:
  - Do not create proposed intents that bypass risk verdict consumption.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `react-native-best-practices` (irrelevant)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: 9,13,14,15
  - **Blocked By**: 3,5,7,8

  **References**:
  - `atlas-gic/prompts/examples/sector_desk.md` - sector output to actionable picks bridge.
  - `atlas-gic/prompts/examples/cio.md` - portfolio action format for intent shaping.

  **Acceptance Criteria**:
  - [ ] Generated proposed intents include rationale, sizing source, and risk provenance.
  - [ ] Tie-break tests confirm unlevered-priority behavior.

  **QA Scenarios**:
  ```
  Scenario: Valid recommendation becomes intent
    Tool: Bash
    Preconditions: Recommendation + PASS risk verdict
    Steps:
      1. Run translator
      2. Assert proposed intent count > 0
      3. Assert each proposed intent includes `risk_reference_id`
    Expected Result: Traceable proposed intents created
    Evidence: .sisyphus/evidence/task-11-intent-pass.txt

  Scenario: Missing risk verdict blocks translation
    Tool: Bash
    Preconditions: Recommendation without risk verdict link
    Steps:
      1. Run translator
      2. Assert zero intents
      3. Assert error code `RISK_VERDICT_REQUIRED`
    Expected Result: Strict dependency enforcement
    Evidence: .sisyphus/evidence/task-11-risk-required.txt
  ```

  **Commit**: YES
  - Message: `feat(intent): map recommendations to approved order intents`

- [ ] 12. Add fail-closed stale-data and no-trade controller

  **What to do**:
  - Implement no-trade decision path for stale, missing, or contradictory critical data.
  - Ensure controller emits explicit audit reason and no order intents.
  - TDD edge tests for data outages and partial provider failures.

  **Must NOT do**:
  - Do not substitute guessed data for required fields.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `ui-ux-pro-max` (not UI)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: 13,15,17
  - **Blocked By**: 2,4,8

  **References**:
  - `atlas-gic/architecture/overview.md` - daily run pipeline with strict stage progression.

  **Acceptance Criteria**:
  - [ ] Missing critical data yields `NO_TRADE` with explicit reason code.
  - [ ] Pipeline exits cleanly without partial order generation.

  **QA Scenarios**:
  ```
  Scenario: Stale data triggers no-trade
    Tool: Bash
    Preconditions: Fixture with stale quote timestamp
    Steps:
      1. Run `python -m app.pipeline.run_daily --mode paper --fixture fixtures/day_stale.json --stage pre_exec`
      2. Assert status `NO_TRADE`
      3. Assert reason code `DATA_STALE`
    Expected Result: No-trade fail-closed behavior
    Evidence: .sisyphus/evidence/task-12-no-trade-stale.txt

  Scenario: Partial provider outage handled
    Tool: Bash
    Preconditions: One critical provider fixture returns null payload
    Steps:
      1. Run `python -m app.pipeline.run_daily --mode paper --fixture fixtures/day_provider_null.json --stage pre_exec`
      2. Assert no intent produced
      3. Assert reason code `CRITICAL_DATA_MISSING`
    Expected Result: Safe halt with audit detail
    Evidence: .sisyphus/evidence/task-12-provider-outage.txt
  ```

  **Commit**: YES
  - Message: `feat(safety): add stale-data no-trade controller`

- [ ] 13. Wire end-to-end daily pipeline runner

  **What to do**:
  - Connect signal -> risk -> approval -> paper-adapter stages in one orchestrated run.
  - Add CLI (or minimal API) invocation for daily multi-day swing workflow.
  - TDD integration around happy path and hard-stop path.

  **Must NOT do**:
  - Do not allow execution path skipping approval/risk checks.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `agent-browser` (not needed)

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after wave 2 dependencies)
  - **Blocks**: 14,15,17,18
  - **Blocked By**: 1,2,4,7,8,9,10,11,12

  **References**:
  - `atlas-gic/architecture/overview.md` - canonical stage ordering.
  - `atlas-gic/architecture/layers.md` - expected flow semantics across layers.

  **Acceptance Criteria**:
  - [ ] One command runs full pipeline to either `NO_TRADE` or `READY_FOR_APPROVAL`/`SUBMITTED_PAPER`.
  - [ ] Stage transitions are logged with schema compliance.

  **QA Scenarios**:
  ```
  Scenario: Full happy-path daily run
    Tool: Bash
    Preconditions: Valid fixture + approved intents + paper mode
    Steps:
      1. Run `python -m app.pipeline.run_daily --mode paper --fixture fixtures/day_ok.json`
      2. Assert terminal status `SUBMITTED_PAPER`
      3. Assert run log includes each stage in order
    Expected Result: End-to-end success
    Evidence: .sisyphus/evidence/task-13-e2e-pass.txt

  Scenario: Daily loss stop path
    Tool: Bash
    Preconditions: Fixture indicates daily drawdown > 2.5%
    Steps:
      1. Run `python -m app.pipeline.run_daily --mode paper --fixture fixtures/day_loss_stop.json`
      2. Assert terminal status `NO_TRADE`
      3. Assert reject code `DAILY_STOP_TRIGGERED`
    Expected Result: Kill-switch precedence enforced
    Evidence: .sisyphus/evidence/task-13-daily-stop.txt
  ```

  **Commit**: YES
  - Message: `feat(pipeline): wire end-to-end daily runner`

- [ ] 14. Add audit and reporting outputs

  **What to do**:
  - Emit structured logs and summary artifacts for signals, risk decisions, approvals, and submissions.
  - Ensure each record contains correlation ids and timestamps.
  - Add tests for report completeness and schema conformance.

  **Must NOT do**:
  - Do not produce opaque logs without identifiers.

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `webapp-testing` (no web)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: 16,F1,F3,F4
  - **Blocked By**: 5,7,9,11,13

  **References**:
  - `atlas-gic/architecture/autoresearch.md` - audit-trail discipline and change traceability.
  - `atlas-gic/results/summary.json` - summary artifact style inspiration.

  **Acceptance Criteria**:
  - [ ] Reports generated for each run include all stage outcomes.
  - [ ] Every order intent references upstream recommendation and risk verdict ids.

  **QA Scenarios**:
  ```
  Scenario: Report completeness
    Tool: Bash
    Preconditions: Successful pipeline run completed
    Steps:
      1. Generate report bundle
      2. Assert files exist for signals/risk/approvals/orders
      3. Assert each row has correlation id
    Expected Result: Complete audit package
    Evidence: .sisyphus/evidence/task-14-report-complete.txt

  Scenario: Missing correlation id rejected
    Tool: Bash
    Preconditions: Inject malformed event without correlation id
    Steps:
      1. Run report validation
      2. Assert non-zero exit code
      3. Assert error includes `correlation_id required`
    Expected Result: Strict audit schema enforcement
    Evidence: .sisyphus/evidence/task-14-correlation-error.txt
  ```

  **Commit**: YES
  - Message: `feat(audit): add structured reporting outputs`

- [ ] 15. Build integration and boundary regression test suite

  **What to do**:
  - Implement integration tests covering cap boundaries, stale data, approval absence, replay attempts, and broker rejection mapping.
  - Add regression set for exact-threshold and off-by-one conditions.
  - Ensure tests validate no-trade and paper-only constraints.

  **Must NOT do**:
  - Do not rely on manual verification for core safety conditions.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `ui-ux-pro-max` (not UI)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: 17,18,F2,F3
  - **Blocked By**: 3,5,6,7,8,9,11,12,13

  **References**:
  - `atlas-gic/results/autoresearch_log.json` - realistic time-series event fixtures for regression patterns.
  - `atlas-gic/architecture/layers.md` - stage interaction expectations.

  **Acceptance Criteria**:
  - [ ] Boundary tests pass at 12.5%, 30%, 1.25x, 2.5% and fail immediately over limits.
  - [ ] Negative tests prove no unapproved or live-mode submission path exists.

  **QA Scenarios**:
  ```
  Scenario: Boundary thresholds exact pass
    Tool: Bash
    Preconditions: Fixture exactly at configured thresholds
    Steps:
      1. Run integration test subset
      2. Assert PASS for exact thresholds
      3. Capture junit output
    Expected Result: Exact boundary behavior is intentional and stable
    Evidence: .sisyphus/evidence/task-15-boundary-pass.xml

  Scenario: Threshold breach fail
    Tool: Bash
    Preconditions: Fixture exceeds threshold by minimal delta
    Steps:
      1. Run `pytest tests/integration/test_limits.py::test_limit_breach_rejected -q`
      2. Assert REJECT path
      3. Assert correct reject code returned
    Expected Result: Immediate hard-stop on breach
    Evidence: .sisyphus/evidence/task-15-boundary-fail.xml
  ```

  **Commit**: YES
  - Message: `test(integration): add boundary and safety regressions`

- [ ] 16. Author operational runbook and safety checklist

  **What to do**:
  - Document startup, daily run, approval workflow, incident handling, and rollback steps.
  - Include explicit do-not-run-live instructions and emergency stop procedure.
  - Add docs tests/lint if configured.

  **Must NOT do**:
  - Do not document live execution instructions for this phase.

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: `humanizer`
  - **Skills Evaluated but Omitted**: `superpowers/test-driven-development` (doc-only)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: F1,F4
  - **Blocked By**: 14

  **References**:
  - `atlas-gic/README.md` - framing and architecture context for operator-facing docs.
  - `atlas-gic/architecture/overview.md` - daily cycle model to mirror operationally.

  **Acceptance Criteria**:
  - [ ] Runbook includes explicit paper-lock verification step.
  - [ ] Checklist includes daily stop and no-trade incident procedures.

  **QA Scenarios**:
  ```
  Scenario: Operator can execute runbook end-to-end
    Tool: interactive_bash
    Preconditions: tmux session with fresh environment
    Steps:
      1. Execute `scripts/runbook_smoke.sh` in tmux session
      2. Confirm each checkpoint status
      3. Save terminal transcript
    Expected Result: Full documented workflow reproducible
    Evidence: .sisyphus/evidence/task-16-runbook-transcript.txt

  Scenario: Missing safety step detected
    Tool: Bash
    Preconditions: Use generated bad runbook fixture `fixtures/docs/runbook_missing_paper_lock.md`
    Steps:
      1. Run `python -m app.docs.validate_runbook --file fixtures/docs/runbook_missing_paper_lock.md`
      2. Assert failure
      3. Assert message flags missing safety step
    Expected Result: Safety documentation guardrail works
    Evidence: .sisyphus/evidence/task-16-doc-safety-error.txt
  ```

  **Commit**: YES
  - Message: `docs(ops): add paper-mode runbook and safety checklist`

- [ ] 17. Execute IBKR paper smoke scenarios

  **What to do**:
  - Run controlled smoke tests against IBKR paper workflow with approved and rejected intents.
  - Verify broker response normalization and reconciliation logs.
  - Capture evidence for successful submit and blocked flows.

  **Must NOT do**:
  - Do not attempt live broker endpoint connectivity.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `superpowers/verification-before-completion`
  - **Skills Evaluated but Omitted**: `agent-browser` (not browser)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocks**: F3
  - **Blocked By**: 2,4,8,10,12,13,15

  **References**:
  - IBKR leveraged ETF margin note: `https://www.ibkrguides.com/kb/article-1124.htm` - helps validate leveraged behavior assumptions.

  **Acceptance Criteria**:
  - [ ] Approved paper intent reaches `submitted_paper`.
  - [ ] Safety-violating intent remains blocked with clear broker/internal reason mapping.

  **QA Scenarios**:
  ```
  Scenario: Paper smoke success
    Tool: Bash
    Preconditions: Valid approved intent fixture
    Steps:
      1. Run smoke command for paper submit
      2. Assert successful submit state
      3. Assert broker order id captured
    Expected Result: End-to-end paper route validated
    Evidence: .sisyphus/evidence/task-17-paper-smoke-pass.txt

  Scenario: Approval-missing smoke fail
    Tool: Bash
    Preconditions: Intent without approval artifact
    Steps:
      1. Run `python -m app.scripts.paper_smoke --fixture fixtures/smoke.no_approval.json`
      2. Assert blocked status
      3. Assert `APPROVAL_REQUIRED`
    Expected Result: Safety gate still enforced in smoke path
    Evidence: .sisyphus/evidence/task-17-paper-smoke-block.txt
  ```

  **Commit**: NO

- [ ] 18. Run deterministic replay regression on fixed snapshots

  **What to do**:
  - Execute pipeline repeatedly over frozen fixtures and compare full outputs.
  - Validate no drift in ranking, sizing, and risk verdicts.
  - Record deterministic hashes per run.

  **Must NOT do**:
  - Do not accept non-deterministic output drift without root-cause fix.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `superpowers/verification-before-completion`
  - **Skills Evaluated but Omitted**: `webapp-testing` (not web)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocks**: F2,F3
  - **Blocked By**: 6,13,15

  **References**:
  - `atlas-gic/results/autoresearch_log.json` - use as realistic sequence patterns for replay fixture crafting.

  **Acceptance Criteria**:
  - [ ] Repeated replay runs produce identical result hashes.
  - [ ] Any drift triggers failing test and investigation artifact.

  **QA Scenarios**:
  ```
  Scenario: Replay hash stability
    Tool: Bash
    Preconditions: Fixed snapshot set
    Steps:
      1. Run replay command 3 times
      2. Compute output hashes each run
      3. Assert all hashes equal
    Expected Result: Deterministic replay confirmed
    Evidence: .sisyphus/evidence/task-18-replay-hashes.txt

  Scenario: Seed perturbation catches drift
    Tool: Bash
    Preconditions: Replay run with explicit divergent seed `--seed 9999`
    Steps:
      1. Run `python -m app.replay.check --fixtures fixtures/replay_set.json --seed 9999`
      2. Assert mismatch detected
      3. Assert test suite fails
    Expected Result: Drift detection operational
    Evidence: .sisyphus/evidence/task-18-drift-detected.txt
  ```

  **Commit**: NO

- [ ] 19. Harden packaging and environment profiles

  **What to do**:
  - Finalize dev and paper profiles, defaulting to paper-safe settings.
  - Add startup validation to refuse unsafe profile combinations.
  - Add tests for profile resolution and safety defaults.

  **Must NOT do**:
  - Do not define or ship default live profile in this phase.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `superpowers/test-driven-development`
  - **Skills Evaluated but Omitted**: `ui-ux-pro-max` (not UI)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4
  - **Blocks**: F2,F4
  - **Blocked By**: 1,2,10

  **References**:
  - `atlas-gic/README.md` - baseline environment framing.

  **Acceptance Criteria**:
  - [ ] Default profile resolves to paper-safe mode.
  - [ ] Unsafe profile combinations fail startup checks.

  **QA Scenarios**:
  ```
  Scenario: Safe default profile
    Tool: Bash
    Preconditions: No explicit env overrides
    Steps:
      1. Run startup validation
      2. Assert active mode `paper`
      3. Assert paper lock message present
    Expected Result: Safe-by-default startup
    Evidence: .sisyphus/evidence/task-19-safe-default.txt

  Scenario: Unsafe combo rejected
    Tool: Bash
    Preconditions: Set conflicting env (paper=false + execution enabled)
    Steps:
      1. Run startup validation
      2. Assert failure
      3. Assert `UNSAFE_PROFILE_COMBINATION`
    Expected Result: Fail-closed profile guard
    Evidence: .sisyphus/evidence/task-19-unsafe-combo.txt
  ```

  **Commit**: YES
  - Message: `chore(profile): harden paper-safe environment profiles`

---

## Final Verification Wave (MANDATORY)

- [ ] F1. **Plan Compliance Audit**
  - Verify each Must Have is implemented and each Must NOT Have is absent.
  - Validate evidence files exist for all task scenarios.
  - Run: `python -m app.audit.plan_compliance --plan .sisyphus/plans/atlas-gic-ibkr-paper-etf-margin.md --evidence .sisyphus/evidence`
  - Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT`

- [ ] F2. **Code Quality Review**
  - Run type/lint/test suite and check for unsafe shortcuts.
  - Run: `pytest -q && python -m app.quality.scan --strict`
  - Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | VERDICT`

- [ ] F3. **Real QA Execution**
  - Execute every QA scenario from every task and collect evidence.
  - Run: `python -m app.qa.run_all --plan .sisyphus/plans/atlas-gic-ibkr-paper-etf-margin.md --evidence .sisyphus/evidence/final-qa`
  - Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check**
  - Ensure work matches plan exactly with no unplanned live-trading additions.
  - Run: `python -m app.audit.scope_fidelity --plan .sisyphus/plans/atlas-gic-ibkr-paper-etf-margin.md --diff-source git`
  - Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- Commit Group 1 (Wave 1): `feat(core): scaffold paper-trading foundation`
- Commit Group 2 (Wave 2): `feat(engine): add signal-risk-approval-execution core`
- Commit Group 3 (Wave 3): `feat(integration): wire pipeline and audit reporting`
- Commit Group 4 (Wave 4): `chore(hardening): add smoke, replay, and profile hardening`

---

## Success Criteria

### Verification Commands
```bash
pytest -q
# Expected: all tests pass

python -m app.pipeline.run_daily --mode paper --fixture fixtures/day_sample.json
# Expected: deterministic recommendation + risk verdict + approval-required order intents
```

### Final Checklist
- [ ] All Must Have requirements present
- [ ] All Must NOT Have constraints enforced
- [ ] TDD suite passes with deterministic replay checks
- [ ] Human approval and paper-only locks proven by negative tests
