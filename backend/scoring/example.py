"""
Example usage of the style scoring system.
Run this to see how the scoring system works.

Usage: python -m scoring.example (from backend directory)
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scoring import score_outfit, load_config, OutfitFeatures

# Example outfit from the spec
example_outfit: OutfitFeatures = {
    "outfitId": "abc123",
    "garments": [
        {
            "id": "top1",
            "type": "top",
            "areaPct": 0.31,
            "colorLAB": (62, -4, -8),
            "material": "cotton",
            "patternType": "plaid",
            "patternStrength": 0.72,
            "glossIndex": 0.1,
        },
        {
            "id": "pant1",
            "type": "bottom",
            "areaPct": 0.41,
            "colorLAB": (50, 0, 0),
            "material": "denim",
            "patternType": "none",
            "patternStrength": 0.0,
            "glossIndex": 0.05,
        },
        {
            "id": "shoe1",
            "type": "accessory",
            "areaPct": 0.06,
            "colorLAB": (60, -5, -7),
            "material": "leather",
            "patternType": "none",
            "patternStrength": 0.0,
            "glossIndex": 0.8,
        },
    ],
    "colorClusters": [
        {"lab": (60, -5, -7), "pct": 0.52},
        {"lab": (48, 2, 4), "pct": 0.30},
        {"lab": (70, -6, -10), "pct": 0.18},
    ],
    "thirdsArea": {"top": 0.35, "mid": 0.30, "bottom": 0.35},
    "domainZ": {"skin": 0.2, "hue": 1.4, "texture": 0.5, "pattern": 0.1},
    "extractionVersion": "segm-1.2.0-kmeans-3",
    "body": None,
}

if __name__ == "__main__":
    print("WearWise Style Scoring System v0.1")
    print("=" * 50)
    
    # Load configuration
    config = load_config()
    print(f"Loaded config version: {config.version}")
    print(f"Weights: {config.weights}")
    print()
    
    # Score the outfit
    result = score_outfit(example_outfit, config)
    
    print(f"Outfit ID: {example_outfit['outfitId']}")
    print(f"Style Score: {result['styleScore']:.1f}/100")
    print()
    
    print("Subscores:")
    for key, value in result["subscores"].items():
        print(f"  {key}: {value:.3f}")
    print()
    
    print("Explanations:")
    for explanation in result["explanations"]:
        print(f"  • {explanation}")
    print()
    
    print("Debug Info:")
    for key, value in result["debug"].items():
        print(f"  {key}: {value}")

