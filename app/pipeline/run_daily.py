"""Daily pipeline runner for IBKR paper trading."""
import argparse
import sys


def main():
    """Main entry point for daily pipeline."""
    parser = argparse.ArgumentParser(
        description="Atlas IBKR Paper Trading Pipeline"
    )
    parser.add_argument(
        "--mode",
        choices=["paper", "live"],
        default="paper",
        help="Execution mode (paper or live)"
    )
    parser.add_argument(
        "--fixture",
        help="Path to market data fixture file (JSON/YAML)"
    )
    parser.add_argument(
        "--stage",
        help="Run up to specific stage (pre_exec, risk, approval, submit)"
    )
    
    args = parser.parse_args()
    
    print(f"Atlas IBKR Paper Trading Pipeline")
    print(f"Mode: {args.mode}")
    print(f"Fixture: {args.fixture or 'none'}")
    print(f"Stage: {args.stage or 'full'}")
    
    if args.mode != "paper":
        print("ERROR: Only paper mode is supported in this phase", file=sys.stderr)
        sys.exit(1)
    
    print("Pipeline ready.")


if __name__ == "__main__":
    main()
