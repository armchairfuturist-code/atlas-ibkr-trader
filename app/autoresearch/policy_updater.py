"""Bounded policy updater for single-change config mutations."""
from dataclasses import dataclass
from typing import Any
import random


@dataclass
class PolicyMutation:
    """Record of a single config mutation."""
    parameter_path: str
    old_value: Any
    new_value: Any
    config_version: str
    reason: str


class PolicyUpdater:
    """Proposes bounded single-change mutations to layer configs."""

    # Mutable parameter paths
    MUTABLE_PATHS = [
        "layer1_macro.agents.central_bank.weight",
        "layer1_macro.agents.inflation.weight",
        "layer1_macro.agents.growth.weight",
        "layer2_sector.sectors.technology.weight",
        "layer2_sector.sectors.healthcare.weight",
        "layer3_superinvestors.filters.buffett_style.weight_bounds",
        "layer4_decision.agents.cro.parameters.max_position_pct",
    ]

    # Safety bounds
    MIN_WEIGHT = 0.01
    MAX_WEIGHT = 1.5
    MAX_DELTA = 0.1

    def __init__(self, seed: int = 42):
        # Use a local Random instance so we never poison the global RNG.
        # Tests can pass a fixed seed for reproducibility; production
        # callers that omit the seed get unpredictable mutations each run.
        self._rng = random.Random(seed)

    def propose(self, base_config: dict, current_version: str) -> PolicyMutation:
        """Propose a single bounded mutation.

        Args:
            base_config: Current config dict
            current_version: Current version string

        Returns:
            PolicyMutation with the change
        """
        # Select random mutable parameter
        path = self._rng.choice(self.MUTABLE_PATHS)

        # Get current value
        old_value = self._get_nested(base_config, path)

        if old_value is None:
            return self._default_mutation(path, current_version)

        # Calculate bounded new value
        delta = self._rng.uniform(-self.MAX_DELTA, self.MAX_DELTA)
        new_value = old_value + delta

        # Clamp to bounds
        new_value = max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, new_value))

        return PolicyMutation(
            parameter_path=path,
            old_value=old_value,
            new_value=round(new_value, 2),
            config_version=current_version,
            reason="Performance-based adjustment",
        )

    def apply(self, config: dict, mutation: PolicyMutation) -> dict:
        """Apply a mutation to a config.

        Args:
            config: Config to modify
            mutation: Mutation to apply

        Returns:
            New config with mutation applied
        """
        # Deep copy
        new_config = self._deep_copy(config)

        # Apply mutation
        self._set_nested(new_config, mutation.parameter_path, mutation.new_value)

        return new_config

    def _get_nested(self, data: dict, path: str) -> Any:
        """Get value from nested dict by dot-separated path."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def _set_nested(self, data: dict, path: str, value: Any) -> None:
        """Set value in nested dict by dot-separated path."""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def _deep_copy(self, data: dict) -> dict:
        """Deep copy a dict."""
        import copy
        return copy.deepcopy(data)

    def _default_mutation(self, path: str, version: str) -> PolicyMutation:
        """Create default mutation when path not found."""
        return PolicyMutation(
            parameter_path=path,
            old_value=0.5,
            new_value=0.55,
            config_version=version,
            reason="Default initialization",
        )
