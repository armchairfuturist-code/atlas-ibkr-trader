"""Qlib data loader — converts yfinance/IBKR data to Qlib format."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class QlibDataLoader:
    """Loads market data and converts it to Qlib-compatible format.

    Bridges the gap between our existing data providers (yfinance, IBKR)
    and Qlib's expected input format (pandas DataFrame with MultiIndex).
    """

    def __init__(self, qlib_provider_uri: Optional[str] = None):
        """Initialize with optional Qlib provider URI.

        Args:
            qlib_provider_uri: Path to Qlib binary data store.
                               If None, Qlib integration is disabled.
        """
        self.provider_uri = qlib_provider_uri
        self._qlib_available = False

        if qlib_provider_uri:
            try:
                import qlib

                qlib.init(provider_uri=qlib_provider_uri, region="us")
                self._qlib_available = True
                logger.info(f"Qlib initialized with provider: {qlib_provider_uri}")
            except Exception as e:
                logger.warning(
                    f"Qlib init failed: {e}. Falling back to rule-based analysis."
                )
                self._qlib_available = False

    @property
    def is_available(self) -> bool:
        """Check if Qlib is available and initialized."""
        return self._qlib_available

    def to_qlib_dataframe(
        self,
        ticker: str,
        prices: list[float],
        volumes: list[float],
        highs: Optional[list[float]] = None,
        lows: Optional[list[float]] = None,
        opens: Optional[list[float]] = None,
        dates: Optional[list[str]] = None,
    ):
        """Convert price data to Qlib-compatible DataFrame.

        Args:
            ticker: Stock symbol
            prices: List of closing prices
            volumes: List of volumes
            highs: Optional list of highs
            lows: Optional list of lows
            opens: Optional list of opens
            dates: Optional list of date strings (YYYY-MM-DD)

        Returns:
            pandas.DataFrame with columns: open, high, low, close, volume
        """
        import pandas as pd

        n = len(prices)

        # Generate dates if not provided
        if dates is None:
            dates = (
                pd.bdate_range(end=pd.Timestamp.today(), periods=n)
                .strftime("%Y-%m-%d")
                .tolist()
            )

        # Build DataFrame
        data = {
            "close": prices,
            "volume": volumes,
        }

        if highs:
            data["high"] = highs
        else:
            data["high"] = [p * 1.01 for p in prices]

        if lows:
            data["low"] = lows
        else:
            data["low"] = [p * 0.99 for p in prices]

        if opens:
            data["open"] = opens
        else:
            data["open"] = prices

        df = pd.DataFrame(data, index=pd.to_datetime(dates))
        df.index.name = "date"

        return df

    def to_qlib_multindex(
        self,
        tickers_data: dict[str, dict],
    ):
        """Convert multiple tickers to Qlib MultiIndex DataFrame.

        Args:
            tickers_data: Dict of ticker -> {prices, volumes, highs, lows, opens, dates}

        Returns:
            pandas.DataFrame with MultiIndex (instrument, datetime)
        """
        import pandas as pd

        frames = []
        for ticker, data in tickers_data.items():
            df = self.to_qlib_dataframe(
                ticker=ticker,
                prices=data.get("prices", []),
                volumes=data.get("volumes", []),
                highs=data.get("highs"),
                lows=data.get("lows"),
                opens=data.get("opens"),
                dates=data.get("dates"),
            )
            df["instrument"] = ticker
            frames.append(df)

        if not frames:
            return pd.DataFrame()

        combined = pd.concat(frames)
        combined.index = pd.MultiIndex.from_arrays(
            [combined["instrument"], combined.index],
            names=["instrument", "datetime"],
        )
        combined = combined.drop(columns=["instrument"])
        combined = combined.sort_index()

        return combined

    def get_qlib_features(
        self,
        tickers: list[str],
        fields: Optional[list[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ):
        """Fetch features from Qlib's expression engine.

        Args:
            tickers: List of stock symbols
            fields: Qlib expression fields (e.g., ['$close', 'Ref($close, 1)'])
            start_time: Start date (YYYY-MM-DD)
            end_time: End date (YYYY-MM-DD)

        Returns:
            pandas.DataFrame with MultiIndex (instrument, datetime)
        """
        if not self._qlib_available:
            logger.warning("Qlib not available, returning empty features")
            return None

        try:
            from qlib.data import D

            if fields is None:
                fields = ["$close", "$volume", "$open", "$high", "$low"]

            return D.features(tickers, fields, start_time=start_time, end_time=end_time)
        except Exception as e:
            logger.error(f"Failed to get Qlib features: {e}")
            return None
