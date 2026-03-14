"""Versioning utilities for config promotion."""
import re
from typing import Any


def bump_version(current: str) -> str:
    """Increment version number.
    
    Args:
        current: Current version string (e.g., "v1", "v2")
        
    Returns:
        Next version string (e.g., "v2", "v3")
    """
    match = re.match(r"v(\d+)", current)
    if match:
        num = int(match.group(1)) + 1
        return f"v{num}"
    return "v2"


def get_version_info(version: str) -> dict[str, Any]:
    """Parse version string into components.
    
    Args:
        version: Version string (e.g., "v1")
        
    Returns:
        Dict with major, minor, and full version
    """
    match = re.match(r"v(\d+)(?:\.(\d+))?", version)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        return {"major": major, "minor": minor, "full": version}
    return {"major": 0, "minor": 0, "full": version}


def is_promotable(source_version: str, target_version: str) -> bool:
    """Check if target version is a valid promotion from source.
    
    Args:
        source_version: Source version
        target_version: Target version
        
    Returns:
        True if target is next version after source
    """
    source_info = get_version_info(source_version)
    target_info = get_version_info(target_version)
    return target_info["major"] == source_info["major"] + 1
