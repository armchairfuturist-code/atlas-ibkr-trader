# Promoted Configurations

This directory stores promoted layer configurations that have passed the shadow-mode replay evaluation.

## Promotion Workflow

1. **Shadow Mode**: Candidate configs run in shadow mode
2. **Replay Evaluation**: Baseline vs candidate compared via replay
3. **Promotion**: If candidate outperforms by ≥5%, config is promoted here
4. **Revert**: If not, reverts to previous baseline

## File Format

Promoted configs follow the same YAML format as base configs, with version incremented (e.g., `v2`, `v3`).

## Safety

- Only paper-trading configs can be promoted
- Hard risk limits are NEVER mutable
- Every promotion has audit trail in decision memory
