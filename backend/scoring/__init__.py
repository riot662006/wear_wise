"""
Style scoring module for WearWise v0.1

Provides quantifiable, replicable, explainable style scores based on
six interpretable factors: Color Harmony, Pattern Balance, Texture Mix,
Highlight Principle, Proportion, and Repetition.
"""

from .types import (
    Material,
    GarmentFeatures,
    OutfitFeatures,
    StyleScore,
)
from .scorer import score_outfit
from .config import load_config, ScoreConfig

__all__ = [
    "Material",
    "GarmentFeatures",
    "OutfitFeatures",
    "StyleScore",
    "score_outfit",
    "load_config",
    "ScoreConfig",
]

