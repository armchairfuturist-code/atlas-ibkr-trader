"""Layer 1: Macro regime detection using real market data via yfinance."""
import logging
from typing import Optional
from datetime import datetime, timedelta

from app.layers.models import MacroAgentOutput
from app.layers.config_loader import load_layer_config

logger = logging.getLogger(__name__)

# Market proxies for macro regime detection
MACRO_TICKERS = {
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "russell2000": "^RUT",
    "vix": "^VIX",
    "tnx_10yr": "^TNX",
    "usd_index": "DX-Y.NYB",
    "gold": "GC=F",
    "crude": "CL=F",
    "emerging": "EEM",
    "bond_agg": "AGG",
}


def _fetch_yfinance(ticker: str) -> Optional[dict]:
    """Fetch price data for a ticker using yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info
        hist = t.history(period="6mo")
        if hist.empty:
            return None
        current = hist["Close"].iloc[-1]
        pct_1m = (current - hist["Close"].iloc[-22]) / hist["Close"].iloc[-22] * 100 if len(hist) >= 22 else 0
        pct_3m = (current - hist["Close"].iloc[-66]) / hist["Close"].iloc[-66] * 100 if len(hist) >= 66 else 0
        sma50 = hist["Close"].rolling(50).mean().iloc[-1] if len(hist) >= 50 else current
        sma200 = hist["Close"].rolling(200).mean().iloc[-1] if len(hist) >= 200 else current
        return {
            "price": current,
            "pct_1m": round(pct_1m, 2),
            "pct_3m": round(pct_3m, 2),
            "above_sma50": current > sma50,
            "above_sma200": current > sma200,
            "name": info.get("shortName", ticker),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch {ticker}: {e}")
        return None


class MacroLayer:
    """Layer 1 - Evaluates macro regime from market data."""

    def __init__(self, config: dict = None):
        self.config = config or load_layer_config("layer1_macro")
        self.version = self.config.get("version", "v1")
        self.agents_cfg = self.config.get("agents", [])
        self.weights = self.config.get("weights", {})

    def evaluate(self) -> list[MacroAgentOutput]:
        """Evaluate macro regime using real market data.

        Returns:
            List of MacroAgentOutput with regime votes and confidence.
        """
        # Fetch real market data
        market_data = {}
        for name, ticker in MACRO_TICKERS.items():
            data = _fetch_yfinance(ticker)
            if data:
                market_data[name] = data

        if not market_data:
            logger.warning("No market data available — using neutral regime")
            return [MacroAgentOutput(
                agent_name="fallback",
                config_version=self.version,
                regime_vote="NEUTRAL",
                confidence=0.5,
                features={},
            )]

        outputs = []

        # Agent 1: Equity Trend
        sp500 = market_data.get("sp500", {})
        if sp500:
            trend = "RISK_ON" if sp500.get("above_sma200", False) and sp500.get("pct_3m", 0) > 0 else \
                    "RISK_OFF" if not sp500.get("above_sma200", True) else "NEUTRAL"
            confidence = min(abs(sp500.get("pct_3m", 0)) / 20, 0.95) + 0.05
            outputs.append(MacroAgentOutput(
                agent_name="equity_trend",
                config_version=self.version,
                regime_vote=trend,
                confidence=round(min(confidence, 1.0), 2),
                features={"sp500_3m_pct": sp500.get("pct_3m", 0)},
            ))

        # Agent 2: Volatility
        vix = market_data.get("vix", {})
        if vix:
            vix_price = vix.get("price", 20)
            regime = "RISK_OFF" if vix_price > 25 else "RISK_ON" if vix_price < 15 else "NEUTRAL"
            confidence = min(abs(vix_price - 20) / 20, 0.9) + 0.05
            outputs.append(MacroAgentOutput(
                agent_name="volatility",
                config_version=self.version,
                regime_vote=regime,
                confidence=round(min(confidence, 1.0), 2),
                features={"vix_price": vix_price},
            ))

        # Agent 3: Broad Market Momentum
        nasdaq = market_data.get("nasdaq", {})
        if nasdaq:
            momentum = nasdaq.get("pct_1m", 0)
            regime = "RISK_ON" if momentum > 2 else "RISK_OFF" if momentum < -2 else "NEUTRAL"
            confidence = min(abs(momentum) / 10, 0.9) + 0.05
            outputs.append(MacroAgentOutput(
                agent_name="market_momentum",
                config_version=self.version,
                regime_vote=regime,
                confidence=round(min(confidence, 1.0), 2),
                features={"nasdaq_1m_pct": momentum},
            ))

        # Agent 4: Small Cap Performance
        russell = market_data.get("russell2000", {})
        if russell:
            regime = "RISK_ON" if russell.get("pct_3m", 0) > 5 else \
                     "RISK_OFF" if russell.get("pct_3m", 0) < -5 else "NEUTRAL"
            confidence = min(abs(russell.get("pct_3m", 0)) / 15, 0.85) + 0.05
            outputs.append(MacroAgentOutput(
                agent_name="small_cap",
                config_version=self.version,
                regime_vote=regime,
                confidence=round(min(confidence, 1.0), 2),
                features={"russell_3m_pct": russell.get("pct_3m", 0)},
            ))

        # Agent 5: Bond Market (risk-off signal when bonds rally)
        bonds = market_data.get("bond_agg", {})
        if bonds:
            regime = "RISK_OFF" if bonds.get("pct_1m", 0) > 1 else \
                     "RISK_ON" if bonds.get("pct_1m", 0) < -1 else "NEUTRAL"
            confidence = min(abs(bonds.get("pct_1m", 0)) / 5, 0.8) + 0.05
            outputs.append(MacroAgentOutput(
                agent_name="bond_safety",
                config_version=self.version,
                regime_vote=regime,
                confidence=round(min(confidence, 1.0), 2),
                features={"bond_1m_pct": bonds.get("pct_1m", 0)},
            ))

        # Agent 6: Gold (risk-off signal)
        gold = market_data.get("gold", {})
        if gold:
            regime = "RISK_OFF" if gold.get("pct_1m", 0) > 3 else \
                     "RISK_ON" if gold.get("pct_1m", 0) < -3 else "NEUTRAL"
            confidence = min(abs(gold.get("pct_1m", 0)) / 10, 0.7) + 0.05
            outputs.append(MacroAgentOutput(
                agent_name="gold_safe_haven",
                config_version=self.version,
                regime_vote=regime,
                confidence=round(min(confidence, 1.0), 2),
                features={"gold_1m_pct": gold.get("pct_1m", 0)},
            ))

        # Agent 7: Yield Curve
        tnx = market_data.get("tnx_10yr", {})
        if tnx:
            yield_val = tnx.get("price", 4.0)
            regime = "RISK_ON" if yield_val > 4.5 else \
                     "RISK_OFF" if yield_val < 3.5 else "NEUTRAL"
            confidence = min(abs(yield_val - 4.0) / 2, 0.75) + 0.05
            outputs.append(MacroAgentOutput(
                agent_name="yield_curve",
                config_version=self.version,
                regime_vote=regime,
                confidence=round(min(confidence, 1.0), 2),
                features={"tnx_yield": yield_val},
            ))

        # Agent 8: Emerging Markets
        em = market_data.get("emerging", {})
        if em:
            regime = "RISK_ON" if em.get("pct_1m", 0) > 2 else \
                     "RISK_OFF" if em.get("pct_1m", 0) < -2 else "NEUTRAL"
            confidence = min(abs(em.get("pct_1m", 0)) / 10, 0.7) + 0.05
            outputs.append(MacroAgentOutput(
                agent_name="emerging_markets",
                config_version=self.version,
                regime_vote=regime,
                confidence=round(min(confidence, 1.0), 2),
                features={"em_1m_pct": em.get("pct_1m", 0)},
            ))

        # Agent 9: US Dollar
        usd = market_data.get("usd_index", {})
        if usd:
            regime = "RISK_ON" if usd.get("pct_1m", 0) < 1 else \
                     "RISK_OFF" if usd.get("pct_1m", 0) > 2 else "NEUTRAL"
            confidence = min(abs(usd.get("pct_1m", 0)) / 5, 0.7) + 0.05
            outputs.append(MacroAgentOutput(
                agent_name="usd_strength",
                config_version=self.version,
                regime_vote=regime,
                confidence=round(min(confidence, 1.0), 2),
                features={"usd_1m_pct": usd.get("pct_1m", 0)},
            ))

        # Agent 10: Oil (inflation/proxy)
        oil = market_data.get("crude", {})
        if oil:
            regime = "RISK_OFF" if oil.get("pct_1m", 0) > 5 else \
                     "RISK_ON" if oil.get("pct_1m", 0) < -5 else "NEUTRAL"
            confidence = min(abs(oil.get("pct_1m", 0)) / 15, 0.65) + 0.05
            outputs.append(MacroAgentOutput(
                agent_name="oil_inflation",
                config_version=self.version,
                regime_vote=regime,
                confidence=round(min(confidence, 1.0), 2),
                features={"oil_1m_pct": oil.get("pct_1m", 0)},
            ))

        logger.info(f"MacroLayer: {sum(1 for o in outputs if o.regime_vote == 'RISK_ON')} risk-on, "
                     f"{sum(1 for o in outputs if o.regime_vote == 'RISK_OFF')} risk-off, "
                     f"{sum(1 for o in outputs if o.regime_vote == 'NEUTRAL')} neutral")
        return outputs
