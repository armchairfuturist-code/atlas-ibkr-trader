#!/usr/bin/env python3
"""13F Filing Tracker & Analysis Module.

Tracks smart money 13F filings and compares with our system's predictions.
Built for Situational Awareness LP (Leopold Aschenbrenner) initially,
extensible to any filer.

Usage:
    python -m app.track_13f --filer "Situational Awareness LP"
    python -m app.track_13f --compare  # Compare with our predictions
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


@dataclass
class ThirteenFHolding:
    """A single 13F holding position."""
    ticker: str
    company: str
    shares: int
    market_value: float  # $USD
    portfolio_weight_pct: float
    type: str = "COMMON"  # COMMON, CALL, PUT
    change_vs_prior_pct: Optional[float] = None
    quarter: str = ""  # e.g., "2025Q4"


@dataclass
class ThirteenFPortfolio:
    """Complete 13F portfolio snapshot."""
    filer_name: str
    quarter: str
    filing_date: str
    total_value: float
    holdings: list[ThirteenFHolding]
    source: str = ""  # where we got the data

    @property
    def top_holdings(self, n: int = 10) -> list[ThirteenFHolding]:
        return sorted(self.holdings, key=lambda h: h.market_value, reverse=True)[:n]

    @property
    def sectors(self) -> dict[str, float]:
        """Aggregate portfolio weight by implied sector."""
        sector_map = {
            "BE": "POWER", "EQT": "POWER", "SEI": "POWER", "LBRT": "POWER",
            "PSIX": "POWER", "BW": "POWER", "PUMP": "POWER", "VST": "POWER",
            "TLN": "POWER", "CEG": "POWER",
            "LITE": "PHOTONICS", "COHR": "PHOTONICS", "TSEM": "PHOTONICS",
            "AAOI": "PHOTONICS", "MTSI": "PHOTONICS",
            "CRWV": "AI_CLOUD", "CORZ": "AI_CLOUD", "APLD": "AI_CLOUD",
            "WYFI": "AI_CLOUD", "KRC": "AI_CLOUD",
            "IREN": "BITCOIN_AI", "CIFR": "BITCOIN_AI", "RIOT": "BITCOIN_AI",
            "HUT": "BITCOIN_AI", "BTDR": "BITCOIN_AI", "CLSK": "BITCOIN_AI",
            "BITF": "BITCOIN_AI",
            "SNDK": "STORAGE",
            "INTC": "SEMI",
            "AVGO": "SEMI", "NVDA": "SEMI", "AMD": "SEMI", "MRVL": "SEMI",
            "MP": "RARE_EARTH", "UUUU": "RARE_EARTH",
            "CSCO": "NETWORKING", "ANET": "NETWORKING", "JNPR": "NETWORKING",
            "FN": "MANUFACTURING",
            "INFY": "IT_SERVICES",
        }
        sectors: dict[str, float] = {}
        for h in self.holdings:
            sec = sector_map.get(h.ticker, "OTHER")
            sectors[sec] = sectors.get(sec, 0) + h.portfolio_weight_pct
        return dict(sorted(sectors.items(), key=lambda x: x[1], reverse=True))


# Known 13F data for Situational Awareness LP
# Source: SEC 13F filing, filed March 2026 for period ending Dec 31, 2025
SITUATIONAL_AWARENESS_Q4_2025 = ThirteenFPortfolio(
    filer_name="Situational Awareness LP",
    quarter="2025Q4",
    filing_date="2026-02-11",
    total_value=4_250_000_000,
    source="SEC EDGAR 13F filing",
    holdings=[
        ThirteenFHolding("BE", "Bloom Energy", 0, 875_510_000, 20.6, "COMMON"),
        ThirteenFHolding("CRWV", "CoreWeave", 10_810_000, 0, 18.2, "CALL"),
        ThirteenFHolding("LITE", "Lumentum", 0, 478_580_000, 11.2, "COMMON"),
        ThirteenFHolding("CORZ", "Core Scientific", 0, 418_690_000, 9.8, "COMMON"),
        ThirteenFHolding("IREN", "IREN Limited", 0, 328_620_000, 7.7, "COMMON"),
        ThirteenFHolding("APLD", "Applied Digital", 0, 278_030_000, 6.5, "COMMON"),
        ThirteenFHolding("SNDK", "SanDisk", 0, 250_250_000, 5.9, "COMMON"),
        ThirteenFHolding("CIFR", "Cipher Mining", 0, 154_520_000, 3.6, "COMMON"),
        ThirteenFHolding("EQT", "EQT Corporation", 0, 133_050_000, 3.1, "COMMON"),
        ThirteenFHolding("COHR", "Coherent", 0, 88_650_000, 2.1, "COMMON"),
        ThirteenFHolding("SEI", "Solaris Energy", 0, 85_800_000, 2.0, "COMMON"),
        ThirteenFHolding("TSEM", "Tower Semiconductor", 0, 84_900_000, 2.0, "COMMON"),
        ThirteenFHolding("RIOT", "Riot Platforms", 0, 78_140_000, 1.8, "COMMON"),
        ThirteenFHolding("KRC", "Kilroy Realty", 0, 49_620_000, 1.2, "COMMON"),
        ThirteenFHolding("HUT", "Hut 8", 0, 39_520_000, 0.9, "COMMON"),
        ThirteenFHolding("WYFI", "WhiteFiber", 0, 27_770_000, 0.7, "COMMON"),
        ThirteenFHolding("PSIX", "Power Solutions", 0, 24_700_000, 0.6, "COMMON"),
        ThirteenFHolding("BTDR", "BitDeer Technologies", 0, 20_040_000, 0.5, "COMMON"),
        ThirteenFHolding("CLSK", "CleanSpark", 0, 16_600_000, 0.4, "COMMON"),
        ThirteenFHolding("BITF", "Bitfarms", 0, 16_210_000, 0.4, "COMMON"),
        ThirteenFHolding("LBRT", "Liberty Energy", 0, 10_470_000, 0.2, "COMMON"),
        ThirteenFHolding("INFY", "Infosys", 500_000, 0, 0.2, "PUT"),
        ThirteenFHolding("PUMP", "ProPetro", 0, 8_660_000, 0.2, "COMMON"),
        ThirteenFHolding("BW", "Babcock & Wilcox", 0, 8_580_000, 0.2, "COMMON"),
        ThirteenFHolding("INTC", "Intel", 1, 37, 0.0, "COMMON"),
    ]
)

# Q4 2025 changes
SITUATIONAL_AWARENESS_EXITS_Q4_2025 = {
    "NVDA": "CLOSED PUTS ($298M notional) - no longer bearish on Nvidia",
    "AVGO": "CLOSED PUTS ($75M notional) - no longer bearish on Broadcom",
    "TSM": "CLOSED PUTS ($75M notional) - no longer bearish on Taiwan Semi",
    "MU": "CLOSED PUTS ($50M notional) - no longer bearish on Micron",
    "GDX": "CLOSED PUTS ($195M notional) - removed macro gold hedge",
    "VST": "SOLD ($252M) - reallocating to direct AI power plays",
    "GLXY": "SOLD ($92M) - exited crypto financial services",
    "WDC": "SOLD ($18M) - consolidated into SNDK",
    "STX": "SOLD ($11M) - consolidated into SNDK",
}


class ThirteenFTracker:
    """
    Tracks 13F filings from smart money managers.

    Currently supports Situational Awareness LP (Leopold Aschenbrenner).
    Extensible to any 13F filer.
    """

    def __init__(self):
        self._filers: dict[str, list[ThirteenFPortfolio]] = {}
        self._seed_known_data()

    def _seed_known_data(self):
        """Seed with manually collected 13F data."""
        self._filers["Situational Awareness LP"] = [
            SITUATIONAL_AWARENESS_Q4_2025
        ]

    def get_portfolio(self, filer: str, quarter: Optional[str] = None) -> Optional[ThirteenFPortfolio]:
        """Get portfolio for a filer, optionally for a specific quarter."""
        portfolios = self._filers.get(filer, [])
        if not portfolios:
            return None
        if quarter:
            for p in portfolios:
                if p.quarter == quarter:
                    return p
            return None
        return portfolios[-1]  # Most recent

    def compare_with_system(self, filer: str = "Situational Awareness LP") -> dict:
        """
        Compare 13F holdings with our system's analysis signals.
        Returns a dict showing alignment/misalignment.
        """
        portfolio = self.get_portfolio(filer)
        if not portfolio:
            return {"error": f"No portfolio data for {filer}"}

        # Our system's recent ratings (from narrative_map.py run)
        # These should ideally come from the system's database
        our_ratings = {
            # Optical/Photonics
            "COHR": {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            "LITE": {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            "MTSI": {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            "AAOI": {"signal": "HOLD", "ensemble": "HOLD", "debate": "BUY"},
            "FN":   {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            # AI Compute
            "NVDA": {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            "AVGO": {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            "MRVL": {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            # Power
            "CEG":  {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            "VST":  {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            "TLN":  {"signal": "BUY",  "ensemble": "HOLD", "debate": "OVERWEIGHT"},
            "EQT":  {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            # Uranium
            "URA":  {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            "URNM": {"signal": "BUY",  "ensemble": "HOLD", "debate": "OVERWEIGHT"},
            "CCJ":  {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
            # Rare Earths
            "MP":   {"signal": "BUY",  "ensemble": "HOLD", "debate": "OVERWEIGHT"},
            "UUUU": {"signal": "BUY",  "ensemble": "HOLD", "debate": "BUY"},
            # Infrastructure
            "CSCO": {"signal": "BUY",  "ensemble": "HOLD", "debate": "OVERWEIGHT"},
            "ANET": {"signal": "HOLD", "ensemble": "HOLD", "debate": "HOLD"},
        }

        comparison = {
            "filer": filer,
            "quarter": portfolio.quarter,
            "total_value": portfolio.total_value,
            "comparison_date": datetime.now().isoformat(),
            "overlapping_holdings": [],
            "holdings_we_dont_cover": [],
            "tickers_we_rate_not_in_portfolio": [],
            "sector_alignment": [],
            "summary": {},
        }

        # Holdings in both
        portfolio_tickers = {h.ticker for h in portfolio.holdings}
        for h in portfolio.holdings:
            if h.ticker in our_ratings:
                ours = our_ratings[h.ticker]
                # Simple alignment: BUY/OVERWEIGHT from us + they hold it = aligned
                aligned = ours["debate"] in ("BUY", "OVERWEIGHT")
                comparison["overlapping_holdings"].append({
                    "ticker": h.ticker,
                    "company": h.company,
                    "fund_weight": h.portfolio_weight_pct,
                    "our_debate": ours["debate"],
                    "our_ensemble": ours["ensemble"],
                    "aligned": aligned,
                })
            else:
                comparison["holdings_we_dont_cover"].append({
                    "ticker": h.ticker,
                    "company": h.company,
                    "fund_weight": h.portfolio_weight_pct,
                })

        # Tickers we rate well that they don't hold
        for ticker, rating in our_ratings.items():
            if ticker not in portfolio_tickers and rating["debate"] in ("BUY", "OVERWEIGHT"):
                comparison["tickers_we_rate_not_in_portfolio"].append({
                    "ticker": ticker,
                    "our_rating": rating["debate"],
                })

        # Sector alignment
        fund_sectors = portfolio.sectors
        our_favored_sectors = ["POWER", "RARE_EARTH", "URANIUM", "PHOTONICS"]
        for sector in our_favored_sectors:
            fund_pct = fund_sectors.get(sector, 0)
            comparison["sector_alignment"].append({
                "sector": sector,
                "fund_allocation_pct": fund_pct,
                "our_view": "BULLISH" if sector in ("POWER", "RARE_EARTH", "URANIUM") else "NEUTRAL",
            })

        # Summary stats
        overlapping = comparison["overlapping_holdings"]
        overlapping_value = sum(
            h["fund_weight"] for h in overlapping
        )
        aligned_count = sum(1 for h in overlapping if h["aligned"])
        misaligned_count = sum(1 for h in overlapping if not h["aligned"])

        comparison["summary"] = {
            "total_fund_holdings": len(portfolio.holdings),
            "overlapping_holdings": len(overlapping),
            "holdings_we_dont_cover": len(comparison["holdings_we_dont_cover"]),
            "tickers_we_rate_not_in_fund": len(comparison["tickers_we_rate_not_in_portfolio"]),
            "aligned_positions": aligned_count,
            "misaligned_positions": misaligned_count,
            "overlapping_value_pct": round(overlapping_value, 1),
        }

        return comparison

    def print_report(self, filer: str = "Situational Awareness LP"):
        """Print a formatted comparison report."""
        comparison = self.compare_with_system(filer)
        if "error" in comparison:
            print(f"Error: {comparison['error']}")
            return

        print("=" * 72)
        print(f"  13F VS SYSTEM COMPARISON")
        print(f"  Filer: {comparison['filer']}  |  Quarter: {comparison['quarter']}")
        print(f"  Fund Value: ${comparison['total_value']:,.0f}")
        print(f"  Date: {comparison['comparison_date'][:10]}")
        print("=" * 72)

        s = comparison["summary"]
        print(f"\n  Holdings overlap: {s['overlapping_holdings']}/{s['total_fund_holdings']}")
        print(f"  Tickers we rate BUY not in fund: {s['tickers_we_rate_not_in_fund']}")
        print(f"  Holdings we don't track: {s['holdings_we_dont_cover']}")
        print(f"  Aligned/Misaligned: {s['aligned_positions']}/{s['misaligned_positions']}")

        # Overlapping
        print(f"\n  {'OVERLAPPING HOLDINGS':^72}")
        print(f"  {'Ticker':<8} {'Weight':>8} {'Our Debate':<14} {'Our Ensemble':<14} {'Aligned?':<10}")
        print(f"  {'-'*56}")
        for h in comparison["overlapping_holdings"]:
            aligned_mark = "✅" if h["aligned"] else "⚠️"
            print(f"  {h['ticker']:<8} {h['fund_weight']:>7.1f}% {h['our_debate']:<14} {h['our_ensemble']:<14} {aligned_mark:<10}")

        # Tickers we rate BUY they don't hold
        if comparison["tickers_we_rate_not_in_portfolio"]:
            print(f"\n  {'TICKERS WE RATE BUY NOT IN FUND':^72}")
            for t in comparison["tickers_we_rate_not_in_portfolio"]:
                print(f"  {t['ticker']:<8} — our rating: {t['our_rating']}")

        # Holdings they have we don't cover
        if comparison["holdings_we_dont_cover"]:
            print(f"\n  {'HOLDINGS WE DONT TRACK (possible signals)':^72}")
            for h in comparison["holdings_we_dont_cover"][:5]:
                print(f"  {h['ticker']:<8} — {h['company'][:40]:<40} ({h['fund_weight']:.1f}%)")

        # Sector alignment
        print(f"\n  {'SECTOR ALIGNMENT':^72}")
        print(f"  {'Sector':<16} {'Fund %':>8} {'Our View':<16}")
        print(f"  {'-'*42}")
        for sa in comparison["sector_alignment"]:
            print(f"  {sa['sector']:<16} {sa['fund_allocation_pct']:>7.1f}% {sa['our_view']:<16}")

        print(f"\n{'='*72}")
        print(f"  REPORT COMPLETE")
        print(f"{'='*72}")


# Also track known exits/hedges for signal
EXITS_AND_HEDGES_Q4_2025 = {
    "CLOSED_BEARISH_HEDGES": {
        "thesis": "No longer sees near-term downside in mega-cap semis",
        "tickers": ["NVDA", "AVGO", "TSM", "MU"],
        "notional_value": 498_000_000,
        "signal": "BULLISH for semis",
    },
    "CLOSED_MACRO_HEDGE": {
        "thesis": "Removed gold hedge — potentially bullish risk appetite",
        "tickers": ["GDX"],
        "notional_value": 195_820_000,
        "signal": "BULLISH risk-on",
    },
    "SOLD_DIRECT_POWER": {
        "thesis": "Exited Vistra to reallocate to more direct AI plays",
        "tickers": ["VST"],
        "value": 252_330_000,
        "signal": "POWER thesis still intact, just restructuring",
    },
    "INTEL_CALL_OPTIONS": {
        "thesis": "20.2M call options retained while liquidating common equity",
        "tickers": ["INTC"],
        "position": "20.2M CALLS",
        "signal": "LEVERAGED BULLISH on Intel turnaround",
    },
}


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="13F Tracker & Analysis")
    parser.add_argument("--filer", default="Situational Awareness LP",
                       help="13F filer name")
    parser.add_argument("--report", action="store_true", default=True,
                       help="Print comparison report")
    parser.add_argument("--save", help="Save report to JSON file")

    args = parser.parse_args()

    tracker = ThirteenFTracker()
    tracker.print_report(args.filer)


if __name__ == "__main__":
    main()
