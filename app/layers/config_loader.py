"""Layer configuration loader for versioned YAML configs."""
import yaml
from pathlib import Path


def get_config_path(layer_name: str, profile: str = "base") -> Path:
    """Get path to layer config file."""
    root = Path(__file__).parent.parent.parent
    return root / "configs" / "layers" / profile / f"{layer_name}.yaml"


def load_layer_config(layer_name: str, profile: str = "base") -> dict:
    """Load layer configuration from versioned YAML file.
    
    Args:
        layer_name: Name of layer (e.g., "layer1_macro")
        profile: Config profile (e.g., "base", "promoted")
    
    Returns:
        Dict with version, agents, weights keys
    """
    config_path = get_config_path(layer_name, profile)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    with open(config_path) as f:
        return yaml.safe_load(f)
