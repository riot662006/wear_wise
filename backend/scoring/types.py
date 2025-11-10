"""
Type definitions for style scoring system.
Matches TypeScript interfaces from spec.
"""

from __future__ import annotations
from typing import Literal, TypedDict, Required, Any

Material = Literal[
    "denim", "cotton", "wool", "knit", "leather", "satin", "silk", "synthetic"
]

PatternType = Literal[
    "none", "solid", "stripe", "plaid", "graphic", "floral", "dots", "other"
]

GarmentType = Literal[
    "top", "bottom", "outer", "dress", "accessory"
]


class GarmentFeatures(TypedDict):
    """Features extracted from a single garment."""
    id: str
    type: GarmentType
    areaPct: float  # 0..1 relative area on body mask
    colorLAB: tuple[float, float, float]  # [L, a, b]
    material: Material
    patternType: PatternType
    patternStrength: float  # 0..1
    glossIndex: float  # 0..1


class ColorCluster(TypedDict):
    """Color cluster from k-means."""
    lab: tuple[float, float, float]  # [L, a, b]
    pct: float  # percentage (0..1)


class ThirdsArea(TypedDict):
    """Area distribution across vertical thirds."""
    top: float
    mid: float
    bottom: float


class DomainZ(TypedDict):
    """Z-scores for highlight principle domains."""
    skin: float
    hue: float
    texture: float
    pattern: float


class BodyMeasurements(TypedDict, total=False):
    """Optional body measurements."""
    waist: float  # cm
    neck: float  # cm


class OutfitFeatures(TypedDict):
    """Complete feature set for an outfit."""
    outfitId: str
    garments: list[GarmentFeatures]
    colorClusters: list[ColorCluster]  # sorted desc by pct
    thirdsArea: ThirdsArea
    domainZ: DomainZ
    body: BodyMeasurements | None
    extractionVersion: str  # model+config hash for reproducibility


class StyleScoreSubscores(TypedDict):
    """Individual subscores in [0,1]."""
    colorHarmony: float
    patternBalance: float
    textureMix: float
    highlightPrinciple: float
    proportion: float
    repetition: float


class StyleScore(TypedDict):
    """Final style score output."""
    version: str  # "scores-0.1.0"
    styleScore: float  # 0..100
    subscores: StyleScoreSubscores
    explanations: list[str]
    debug: dict[str, Any] | None

