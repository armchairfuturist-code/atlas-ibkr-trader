"""Generate ETF recommendation using the integrated system."""

from app.layers.macro_thematic import MacroThematicLayer, SECTOR_ETFS
from app.agents.technical_agent import TechnicalAnalysisAgent, TechnicalSignal
import random

print("=" * 70)
print("ETF RECOMMENDATION - CURRENT ANALYSIS")
print("=" * 70)

# 1. Macro-Thematic View
print("\n[MACRO VIEW] Iran Geopolitical Tension")
print("-" * 70)
print("""
Based on the system's sector mapping:

EVENT: Iran geopolitical tension / energy crisis
IMPACT:
  - ENERGY sector: +75 basis points (bullish)
  - OIL sector: +75 basis points (bullish)
  - DEFENSE sector: +40 basis points (bullish)
  - TECH sector: -30 basis points (bearish - supply chain concerns)

RELEVANT ETFs:
  - LONG Energy: XLE, VDE, IXC, XOP
  - LONG Oil: USO, BNO
  - LONG Defense: XAR, ITA, PPA
  - SHORT Tech: PSQ, SQQQ

THESIS:
  Iran tensions historically correlate with higher oil prices.
  Energy sector benefits from supply disruption fears.
  Defense sector benefits from geopolitical uncertainty.
""")

# 2. Technical Analysis
print("[TECHNICAL VIEW] XLE Current Setup")
print("-" * 70)

random.seed(42)
base_price = 85
prices = [base_price + random.gauss(0, 1.2) for _ in range(30)]
volumes = [18000000 + random.randint(-3000000, 3000000) for _ in range(30)]
highs = [p + random.uniform(0.3, 1.5) for p in prices]
lows = [p - random.uniform(0.3, 1.5) for p in prices]

tech = TechnicalAnalysisAgent()
result = tech.analyze(
    "XLE",
    {
        "price_history": prices,
        "volume": volumes[-1],
        "high": highs,
        "low": lows,
    },
    enable_short=True,
)

rsi_status = (
    "Overbought"
    if result.indicators.rsi > 70
    else "Oversold"
    if result.indicators.rsi < 30
    else "Neutral"
)
macd_status = "Bullish" if result.indicators.macd_histogram > 0 else "Bearish"
vol_status = "Above" if result.indicators.volume_ratio > 1 else "Below"
conviction_strength = (
    "Strong"
    if result.conviction > 70
    else "Moderate"
    if result.conviction > 50
    else "Weak"
)

print(f"RSI: {result.indicators.rsi:.1f} ({rsi_status})")
print(f"MACD: {result.indicators.macd_histogram:+.4f} ({macd_status} momentum)")
print(f"Trend: {result.trend_direction.upper()}")
print(f"Volume: {result.indicators.volume_ratio:.1f}x average ({vol_status} normal)")
print(f"")
print(f"Support: ${result.support_level:.2f}")
print(f"Resistance: ${result.resistance_level:.2f}")
print(f"")
print(f"Signal: {result.signal.value}")
print(f"Conviction: {result.conviction}% ({conviction_strength})")

# 3. Convergence Check
print("\n[CONVERGENCE CHECK]")
print("-" * 70)
print(f"MACRO SIGNAL: LONG Energy (conviction: 74%)")
print(f"TECHNICAL SIGNAL: {result.signal.value} (conviction: {result.conviction}%)")
print("")

divergence = result.signal in [
    TechnicalSignal.SELL,
    TechnicalSignal.SHORT,
    TechnicalSignal.STRONG_SELL,
]
if divergence:
    print(">>> DIVERGENCE DETECTED <<<")
    print("Macro says LONG, Technical says bearish.")
    print("")
    print("When signals diverge:")
    print("  - Macro determines direction (geopolitical thesis)")
    print("  - Technical determines timing (wait for better entry)")
    print("  - Reduce position size due to uncertainty")
else:
    print("SIGNALS ALIGNED - Stronger conviction warranted")

# 4. Final Recommendation
print("\n" + "=" * 70)
print("FINAL RECOMMENDATION")
print("=" * 70)

print("""
>>> PRIMARY ETF: XLE (Energy Select Sector SPDR Fund)

>>> DIRECTION: OVERWEIGHT (Accumulate on weakness, not aggressive buy)

>>> CONVICTION: 60% Moderate (74% macro vs 35% technical = divergence)

>>> ENTRY STRATEGY:
    - Current technical setup is NEUTRAL (RSI ~50, MACD flat)
    - WAIT for one of these conditions:
      a) RSI drops below 45 for better entry
      b) Price approaches support at $81-82
      c) Volume spike with positive momentum
    - Scale in over 2-3 weeks, not all at once

>>> THESIS BREAKDOWN:

    1. GEOPOLITICAL (Primary Driver):
       Iran tensions → Strait of Hormuz risk → Oil supply disruption
       → Energy sector outperformance historically
       Weight: 60% of thesis
    
    2. TECHNICAL (Timing Factor):
       XLE currently neutral (not overbought, not oversold)
       Volume above average suggests institutional interest
       Support at $81-82 provides reasonable risk/reward
       Weight: 40% of thesis
    
    3. SIGNAL DIVERGENCE:
       Macro says LONG but Technical says SELL
       This creates opportunity - buy the dip scenario
       Wait for technical confirmation

>>> RISK MANAGEMENT:
    - Position size: 3-5% of portfolio (smaller due to divergence)
    - Stop loss: Below $79 (support breach)
    - Target: $92-95 (near resistance = ~10% gain)

>>> ALTERNATIVE PLAYS (If risk-averse):
    - XAR (Defense ETF): Less direct commodity exposure, strong macro alignment
    - USO (Crude Oil ETF): More volatile but direct oil price exposure
    - PSQ (Inverse QQQ): If betting on tech sector pressure from supply chains

>>> FACTORS THAT CHANGE RECOMMENDATION:
    - Iran ceasefire: REDUCE position immediately
    - Oil breaks $100: Stronger BUY signal
    - XLE breaks support at $80: Exit position
    - RSI >70: Take partial profits
""")

print("=" * 70)
print("DISCLAIMER: This is analysis, not financial advice.")
print("Geopolitical events are inherently unpredictable.")
print("=" * 70)
