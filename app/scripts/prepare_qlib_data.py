"""Prepare Qlib training data from yfinance.

Downloads historical OHLCV data for a configurable ETF/stock universe
and converts it to Qlib's binary format.

Usage:
    python scripts/prepare_qlib_data.py [--output qlib_data] [--years 3] [--universe etf]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default ETF universe for training
DEFAULT_ETF_UNIVERSE = [
    # Sector ETFs
    "XLE",
    "XLF",
    "XLK",
    "XLI",
    "XLP",
    "XLU",
    "XLV",
    "XLY",
    "XLB",
    "XLRE",
    # Broad market
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    # Thematic
    "XAR",
    "USO",
    "GLD",
    "TLT",
    "HYG",
    "LQD",
    # International
    "EFA",
    "EEM",
    "FXI",
    "EWJ",
]

DEFAULT_STOCK_UNIVERSE = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "META",
    "TSLA",
    "BRK-B",
    "JPM",
    "JNJ",
    "V",
    "PG",
    "XOM",
    "UNH",
    "HD",
    "MA",
    "DIS",
    "BAC",
]


def download_yfinance_data(
    tickers: list[str],
    start_date: str,
    end_date: str,
) -> dict[str, list[dict]]:
    """Download OHLCV data from yfinance.

    Returns:
        Dict of ticker -> list of {date, open, high, low, close, volume}
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed. pip install yfinance")
        return {}

    data = {}
    for i, ticker in enumerate(tickers, 1):
        try:
            logger.info(f"[{i}/{len(tickers)}] Downloading {ticker}...")
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if df.empty:
                logger.warning(f"No data for {ticker}")
                continue

            # Flatten multi-level columns if present
            if isinstance(df.columns, type(df.columns)):
                if df.columns.nlevels > 1:
                    df.columns = df.columns.droplevel(1)

            bars = []
            for date, row in df.iterrows():
                date_str = (
                    date.strftime("%Y-%m-%d")
                    if hasattr(date, "strftime")
                    else str(date)
                )
                bars.append(
                    {
                        "date": date_str,
                        "open": float(row.get("Open", row.get("open", 0))),
                        "high": float(row.get("High", row.get("high", 0))),
                        "low": float(row.get("Low", row.get("low", 0))),
                        "close": float(row.get("Close", row.get("close", 0))),
                        "volume": float(row.get("Volume", row.get("volume", 0))),
                    }
                )

            if bars:
                data[ticker] = bars
                logger.info(f"  {ticker}: {len(bars)} bars downloaded")

        except Exception as e:
            logger.warning(f"Failed to download {ticker}: {e}")

    return data


def save_as_csv(
    data: dict[str, list[dict]],
    output_dir: Path,
):
    """Save data as CSV files (one per ticker) for Qlib ingestion."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(exist_ok=True)

    for ticker, bars in data.items():
        csv_path = csv_dir / f"{ticker}.csv"
        with open(csv_path, "w") as f:
            f.write("date,open,high,low,close,volume\n")
            for bar in bars:
                f.write(
                    f"{bar['date']},{bar['open']:.4f},{bar['high']:.4f},"
                    f"{bar['low']:.4f},{bar['close']:.4f},{bar['volume']:.0f}\n"
                )
        logger.info(f"Saved {csv_path} ({len(bars)} bars)")


def save_as_json(
    data: dict[str, list[dict]],
    output_dir: Path,
):
    """Save data as JSON for the Qlib adapter to use directly."""
    import json

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "market_data.json"

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved {json_path} ({len(data)} tickers)")

    # Also save a summary
    summary = {
        "tickers": list(data.keys()),
        "total_tickers": len(data),
        "date_range": {
            "earliest": min(bars[0]["date"] for bars in data.values() if bars),
            "latest": max(bars[-1]["date"] for bars in data.values() if bars),
        },
        "total_bars": sum(len(bars) for bars in data.values()),
    }

    summary_path = output_dir / "data_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Saved {summary_path}")


def convert_to_qlib_bin(
    csv_dir: Path,
    qlib_dir: Path,
):
    """Convert CSV data to Qlib binary format using dump_bin.py."""
    try:
        import qlib
    except ImportError:
        logger.warning("Qlib not installed — skipping binary conversion.")
        logger.info("Install with: pip install pyqlib (Python 3.8-3.12 required)")
        return False

    try:
        from qlib.dump_bin import DumpDataAll

        qlib_dir.mkdir(parents=True, exist_ok=True)

        dump = DumpDataAll(
            csv_path=str(csv_dir),
            qlib_dir=str(qlib_dir),
            max_workers=4,
            exclude_fields="date,symbol",
            date_field_name="date",
            symbol_field_name="symbol",
        )
        dump.dump()

        logger.info(f"Qlib binary data saved to {qlib_dir}")
        return True

    except Exception as e:
        logger.warning(f"Binary conversion failed: {e}")
        logger.info("You can still use the JSON data with the Qlib adapter.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Prepare Qlib training data from yfinance"
    )
    parser.add_argument("--output", default="qlib_data", help="Output directory")
    parser.add_argument("--years", type=int, default=3, help="Years of historical data")
    parser.add_argument(
        "--universe",
        choices=["etf", "stock", "both"],
        default="etf",
        help="Ticker universe to download",
    )
    parser.add_argument(
        "--tickers", nargs="+", help="Custom ticker list (overrides --universe)"
    )

    args = parser.parse_args()

    # Determine tickers
    if args.tickers:
        tickers = args.tickers
    elif args.universe == "etf":
        tickers = DEFAULT_ETF_UNIVERSE
    elif args.universe == "stock":
        tickers = DEFAULT_STOCK_UNIVERSE
    else:
        tickers = DEFAULT_ETF_UNIVERSE + DEFAULT_STOCK_UNIVERSE

    # Date range
    from datetime import datetime, timedelta

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=args.years * 365)).strftime(
        "%Y-%m-%d"
    )

    output_dir = Path(args.output)

    print("=" * 60)
    print("Qlib Data Preparation")
    print("=" * 60)
    print(f"Tickers: {len(tickers)} ({args.universe})")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Output: {output_dir}")
    print()

    # Download data
    logger.info("Downloading data from yfinance...")
    data = download_yfinance_data(tickers, start_date, end_date)

    if not data:
        logger.error("No data downloaded. Check your internet connection.")
        sys.exit(1)

    logger.info(f"Downloaded data for {len(data)} tickers")

    # Save as CSV
    logger.info("Saving as CSV...")
    save_as_csv(data, output_dir)

    # Save as JSON (for adapter)
    logger.info("Saving as JSON...")
    save_as_json(data, output_dir)

    # Try Qlib binary conversion
    logger.info("Attempting Qlib binary conversion...")
    qlib_dir = output_dir / "qlib_bin"
    csv_dir = output_dir / "csv"
    convert_to_qlib_bin(csv_dir, qlib_dir)

    print()
    print("=" * 60)
    print("Data preparation complete!")
    print("=" * 60)
    print(f"\nFiles saved to: {output_dir}/")
    print(f"  - csv/          : Individual CSV files per ticker")
    print(f"  - market_data.json : All data in JSON format")
    print(f"  - data_summary.json : Data summary")
    if (qlib_dir).exists():
        print(f"  - qlib_bin/     : Qlib binary format")
    print(f"\nNext step: Train model")
    print(f"  python scripts/train_qlib_model.py --data {output_dir}")


if __name__ == "__main__":
    main()
