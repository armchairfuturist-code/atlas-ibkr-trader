"""Tool to check ETF universe."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.universe import load_universe, ETFType


def main():
    parser = argparse.ArgumentParser(description="Check ETF universe")
    parser.add_argument("--file", required=True, help="Path to universe YAML file")
    args = parser.parse_args()
    
    try:
        universe = load_universe(args.file)
        
        print(f"ETF Universe loaded: {len(universe.etfs)} ETFs")
        
        # Check for at least one unlevered and one leveraged
        unlevered = [e for e in universe.etfs if e.etf_type == ETFType.UNLEVERED]
        leveraged = [e for e in universe.etfs if "levered" in e.etf_type.value]
        
        print(f"Unlevered ETFs: {len(unlevered)}")
        print(f"Leveraged ETFs: {len(leveraged)}")
        
        if len(unlevered) == 0:
            print("ERROR: No unlevered ETFs found", file=sys.stderr)
            return 1
        if len(leveraged) == 0:
            print("ERROR: No leveraged ETFs found", file=sys.stderr)
            return 1
            
        print("Universe validation: PASSED")
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
