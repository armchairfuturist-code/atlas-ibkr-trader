"""Tools module for validation and checks."""
import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config, ExecutionMode, load_config_from_file


def main():
    """Validate config file."""
    parser = argparse.ArgumentParser(description="Validate configuration")
    parser.add_argument("--config", required=True, help="Path to config YAML file")
    args = parser.parse_args()
    
    try:
        config = load_config_from_file(args.config)
        
        is_valid, error = config.validate_for_submission()
        
        if is_valid:
            print(f"Config validated successfully")
            print(f"Mode: {config.mode.value}")
            print(f"Paper lock enabled: {config.is_paper_only()}")
            print(f"Risk limits: gross={config.risk_limits.max_gross_leverage}x, "
                  f"position={config.risk_limits.max_position_pct}%, "
                  f"sector={config.risk_limits.max_sector_pct}%, "
                  f"daily_stop={config.risk_limits.daily_loss_stop_pct}%")
            return 0
        else:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
            
    except Exception as e:
        print(f"ERROR: Config validation failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
