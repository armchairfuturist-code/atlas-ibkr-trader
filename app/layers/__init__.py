"""Layer evaluation modules for ATLAS decision stack.

Layers:
- MacroThematic: Geopolitical event analysis and sector recommendations
- Layer1 (Macro): Macro regime detection
- Layer2 (Sector): Sector scoring
- Layer3 (Superinvestor): Superinvestor tracking
- Layer4 (Decision): Final decision synthesis
"""

from app.layers.macro_thematic import (
    MacroThematicLayer,
    MacroThematicReport,
    SectorRecommendation,
    ThematicDirection,
    macro_thematic_layer,
)

__all__ = [
    "MacroThematicLayer",
    "MacroThematicReport",
    "SectorRecommendation",
    "ThematicDirection",
    "macro_thematic_layer",
]
