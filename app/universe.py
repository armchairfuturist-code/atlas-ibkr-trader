"""ETF Universe module with leverage and sector metadata."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import yaml


class ETFType(str, Enum):
    """ETF type classification."""
    UNLEVERED = "unlevered"
    LEVERED_2X = "levered_2x"
    LEVERED_3X = "levered_3x"
    INVERSE = "inverse"
    INVERSE_LEVERED = "inverse_levered"


class Sector(str, Enum):
    """Sector classification."""
    TECHNOLOGY = "technology"
    ENERGY = "energy"
    FINANCIALS = "financials"
    HEALTHCARE = "healthcare"
    CONSUMER = "consumer"
    INDUSTRIALS = "industrials"
    MATERIALS = "materials"
    UTILITIES = "utilities"
    REAL_ESTATE = "real_estate"
    COMMUNICATION = "communication"
    BROAD_MARKET = "broad_market"
    COMMODITIES = "commodities"
    BONDS = "bonds"


class ETF(BaseModel):
    """ETF with metadata."""
    ticker: str = Field(min_length=1, max_length=10)
    name: str
    etf_type: ETFType
    primary_sector: Sector
    leverage_factor: float = Field(ge=-3.0, le=3.0)
    is_inverse: bool = False
    
    # Liquidity thresholds
    min_adverage_volume: int = Field(default=100000, ge=0)
    max_spread_bps: float = Field(default=50.0, ge=0)
    
    @field_validator("is_inverse", mode="before")
    @classmethod
    def compute_inverse_flag(cls, v, info):
        """Auto-compute inverse flag from type."""
        if v:
            return v
        data = info.data
        if "etf_type" in data:
            etf_type = data["etf_type"]
            if "inverse" in etf_type.value:
                return True
        return False
    
    def effective_exposure(self, notional: float) -> float:
        """Calculate effective exposure accounting for leverage."""
        return notional * self.leverage_factor


class ETFUniverse(BaseModel):
    """Collection of ETFs in the universe."""
    version: str = "1.0"
    etfs: list[ETF] = Field(min_length=1)
    
    def get_by_ticker(self, ticker: str) -> Optional[ETF]:
        """Find ETF by ticker symbol."""
        for etf in self.etfs:
            if etf.ticker.upper() == ticker.upper():
                return etf
        return None
    
    def get_by_sector(self, sector: Sector) -> list[ETF]:
        """Get all ETFs in a sector."""
        return [etf for etf in self.etfs if etf.primary_sector == sector]
    
    def get_unlevered_priority(self) -> list[ETF]:
        """Get ETFs sorted with unlevered first (for tie-breaking)."""
        return sorted(
            self.etfs,
            key=lambda e: (0 if e.etf_type == ETFType.UNLEVERED else 1, e.ticker)
        )


def load_universe(path: str) -> ETFUniverse:
    """Load ETF universe from YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return ETFUniverse(**data)
