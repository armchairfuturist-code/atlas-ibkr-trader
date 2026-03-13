"""Config module for trading system."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ExecutionMode(str, Enum):
    """Execution mode for the trading system."""
    PAPER = "paper"
    LIVE = "live"


class RiskLimits(BaseModel):
    """Risk limits configuration."""
    max_gross_leverage: float = Field(default=1.25, ge=1.0, le=5.0)
    max_position_pct: float = Field(default=12.5, ge=1.0, le=50.0)
    max_sector_pct: float = Field(default=30.0, ge=1.0, le=100.0)
    daily_loss_stop_pct: float = Field(default=2.5, ge=0.1, le=20.0)
    
    @field_validator("max_gross_leverage")
    @classmethod
    def validate_leverage(cls, v: float) -> float:
        if v > 2.0:
            raise ValueError("Gross leverage > 2.0 requires additional risk approval")
        return v


class Config(BaseModel):
    """Main configuration for the trading system."""
    mode: ExecutionMode = Field(default=ExecutionMode.PAPER)
    risk_limits: RiskLimits = Field(default_factory=RiskLimits)
    
    # IBKR settings
    ibkr_host: str = Field(default="127.0.0.1")
    ibkr_port: int = Field(default=7497)  # Paper default
    ibkr_client_id: int = Field(default=1, ge=0, le=999)
    
    # Execution settings
    require_human_approval: bool = Field(default=True)
    
    def is_paper_only(self) -> bool:
        """Check if running in paper mode."""
        return self.mode == ExecutionMode.PAPER
    
    def validate_for_submission(self) -> tuple[bool, Optional[str]]:
        """
        Validate config allows order submission.
        Returns (is_valid, error_message)
        """
        if self.mode != ExecutionMode.PAPER:
            return False, "live mode blocked: only paper mode allows submission"
        return True, None


def load_config_from_file(path: str) -> Config:
    """Load configuration from YAML file."""
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    return Config(**data)
