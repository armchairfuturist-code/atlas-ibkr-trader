"""Test script for Macro-Thematic Layer.

Run this to verify the Iran crisis → commodity impact mapping works.
"""

import sys
import os

# Add the implementation directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.layers.macro_thematic import MacroThematicLayer, ThematicDirection


def test_macro_thematic_layer():
    """Test the MacroThematicLayer functionality."""
    print("\n" + "=" * 60)
    print("TEST: Macro-Thematic Layer Analysis")
    print("=" * 60)

    layer = MacroThematicLayer()

    # Test analyze
    print("\n1. Testing analyze()...")
    report = layer.analyze()
    print(f"   Theme: {report.theme}")
    print(f"   Probability: {report.probability:.1%}")
    print(f"   Overall Direction: {report.overall_direction.value}")
    print(f"   Confidence: {report.confidence}")

    if report.sector_recommendations:
        print(f"\n   Sector Recommendations ({len(report.sector_recommendations)}):")
        for rec in report.sector_recommendations[:3]:
            print(
                f"     - {rec.sector}: {rec.direction.value} (conviction: {rec.conviction})"
            )
            if rec.etf_tickers:
                print(f"       ETFs: {', '.join(rec.etf_tickers[:2])}")

    if report.key_events:
        print(f"\n   Key Events ({len(report.key_events)}):")
        for event in report.key_events[:2]:
            print(f"     - {event[:70]}...")


def test_specific_theme():
    """Test analysis for specific theme (Iran)."""
    print("\n" + "=" * 60)
    print("TEST: Iran-Specific Analysis")
    print("=" * 60)

    layer = MacroThematicLayer()

    print("\n1. Testing analyze(theme='iran')...")
    report = layer.analyze(theme="iran")
    print(f"   Theme: {report.theme}")
    print(f"   Probability: {report.probability:.1%}")
    print(f"   Thesis:\n   {report.thesis[:200]}...")


def test_etf_recommendations():
    """Test ETF recommendation system."""
    print("\n" + "=" * 60)
    print("TEST: ETF Recommendations")
    print("=" * 60)

    layer = MacroThematicLayer()

    print("\n1. Testing LONG recommendations...")
    long_energy = layer.recommend_etf("ENERGY", ThematicDirection.LONG)
    print(f"   LONG ENERGY: {long_energy}")

    long_defense = layer.recommend_etf("DEFENSE", ThematicDirection.LONG)
    print(f"   LONG DEFENSE: {long_defense}")

    print("\n2. Testing SHORT recommendations...")
    short_energy = layer.recommend_etf("ENERGY", ThematicDirection.SHORT)
    print(f"   SHORT ENERGY: {short_energy}")

    short_tech = layer.recommend_etf("TECH", ThematicDirection.SHORT)
    print(f"   SHORT TECH: {short_tech}")


def test_best_plays():
    """Test getting best trading plays."""
    print("\n" + "=" * 60)
    print("TEST: Best Trading Plays")
    print("=" * 60)

    layer = MacroThematicLayer()

    print("\n1. Getting top 3 plays...")
    plays = layer.get_best_plays(max_plays=3)

    if plays:
        print(f"\n   Found {len(plays)} trading plays:")
        for i, play in enumerate(plays, 1):
            print(f"\n   Play {i}:")
            print(f"     Sector: {play['sector']}")
            print(f"     Direction: {play['direction']}")
            print(f"     Conviction: {play['conviction']}")
            print(f"     ETFs: {play['etfs']}")
            print(f"     Thesis: {play['thesis'][:60]}...")
    else:
        print("   No trading plays found (may need Polymarket data)")


def test_sector_impacts():
    """Test sector impact mappings."""
    print("\n" + "=" * 60)
    print("TEST: Sector Impact Mappings")
    print("=" * 60)

    from app.layers.macro_thematic import EVENT_THEMES, SECTOR_ETFS

    print("\n1. Available Themes:")
    for theme_key, theme_data in EVENT_THEMES.items():
        print(f"   - {theme_key}: {theme_data['theme']}")

    print("\n2. Sector ETF Mappings:")
    for sector, etfs in list(SECTOR_ETFS.items())[:3]:
        long_etfs = etfs.get("long", [])
        short_etfs = etfs.get("short", [])
        print(f"   {sector}:")
        print(f"     LONG: {long_etfs}")
        if short_etfs:
            print(f"     SHORT: {short_etfs}")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MACRO-THEMATIC LAYER TEST SUITE")
    print("=" * 60)

    test_macro_thematic_layer()
    test_specific_theme()
    test_etf_recommendations()
    test_best_plays()
    test_sector_impacts()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
    print("\nKey capabilities:")
    print("1. Maps geopolitical events to sector impacts")
    print("2. Generates thematic recommendations (LONG/SHORT)")
    print("3. Recommends specific ETFs for each sector")
    print("4. Integrates with Polymarket for probability data")


if __name__ == "__main__":
    main()
