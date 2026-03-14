"""Decision memory for persisting run records and outcomes."""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class RunRecord:
    """Record of a single decision run."""
    run_id: str
    config_version: str
    proposals: list[dict[str, Any]]
    rationale: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    outcomes: Optional[dict[str, Any]] = None


class DecisionMemory:
    """Append-only store for decision runs and outcomes."""
    
    def __init__(self, path: Path | str):
        """Initialize with path to JSONL file.
        
        Args:
            path: Path to the memory file (JSONL format)
        """
        self.path = Path(path)
        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def append_run(self, record: RunRecord) -> None:
        """Append a run record to memory.
        
        Args:
            record: RunRecord to append
        """
        with open(self.path, "a") as f:
            f.write(json.dumps(asdict(record)) + "\n")
    
    def append_outcome(self, run_id: str, outcome: dict[str, Any]) -> None:
        """Append realized outcome for a run.
        
        Args:
            run_id: ID of the run
            outcome: Outcome data (e.g., returns, pnl)
        """
        # Load existing runs, update the matching one
        runs = self.load_runs()
        
        for run in runs:
            if run.run_id == run_id:
                run.outcomes = outcome
                break
        
        # Rewrite all records
        self._rewrite_records(runs)
    
    def load_runs(self) -> list[RunRecord]:
        """Load all run records from memory.
        
        Returns:
            List of RunRecord objects
        """
        if not self.path.exists():
            return []
        
        runs = []
        with open(self.path) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    runs.append(RunRecord(**data))
        return runs
    
    def _rewrite_records(self, records: list[RunRecord]) -> None:
        """Rewrite all records to file."""
        with open(self.path, "w") as f:
            for record in records:
                f.write(json.dumps(asdict(record)) + "\n")
    
    def get_runs_since(self, since: str) -> list[RunRecord]:
        """Get runs after a given timestamp.
        
        Args:
            since: ISO timestamp string
            
        Returns:
            List of RunRecord objects
        """
        all_runs = self.load_runs()
        return [r for r in all_runs if r.timestamp >= since]
