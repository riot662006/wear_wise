"""
Configuration loader for style scoring.
"""

from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any


@dataclass
class ColorConfig:
    """Color harmony thresholds."""
    dMin: float = 8.0  # minimum CIEDE2000 distance (too close = muddy)
    dMax: float = 35.0  # maximum CIEDE2000 distance (too far = clashing)
    tauH: float = 10.0  # temperature parameter for harmony penalty


@dataclass
class PatternConfig:
    """Pattern balance thresholds."""
    strong: float = 0.6  # patternStrength >= this is "strong"
    mild: float = 0.3  # patternStrength in [mild, strong) is "mild"


@dataclass
class TextureConfig:
    """Texture mix parameters."""
    glossBonus: float = 0.1  # bonus if exactly one glossy piece


@dataclass
class HighlightConfig:
    """Highlight principle thresholds."""
    zThreshold: float = 1.0  # z-score threshold for "highlighted" domain


@dataclass
class ProportionConfig:
    """Proportion scoring parameters."""
    idealTop: float = 0.33  # ideal top third ratio
    tolerance: float = 0.17  # tolerance around ideal


@dataclass
class ScoreConfig:
    """Complete scoring configuration."""
    version: str
    weights: dict[str, float]  # C, P, T, H, B, R
    color: ColorConfig
    pattern: PatternConfig
    texture: TextureConfig
    highlight: HighlightConfig
    proportion: ProportionConfig

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScoreConfig:
        """Load from dictionary (e.g., from JSON)."""
        return cls(
            version=data["version"],
            weights=data["weights"],
            color=ColorConfig(**data["color"]),
            pattern=PatternConfig(**data["pattern"]),
            texture=TextureConfig(**data["texture"]),
            highlight=HighlightConfig(**data["highlight"]),
            proportion=ProportionConfig(**data["proportion"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "weights": self.weights,
            "color": {
                "dMin": self.color.dMin,
                "dMax": self.color.dMax,
                "tauH": self.color.tauH,
            },
            "pattern": {
                "strong": self.pattern.strong,
                "mild": self.pattern.mild,
            },
            "texture": {
                "glossBonus": self.texture.glossBonus,
            },
            "highlight": {
                "zThreshold": self.highlight.zThreshold,
            },
            "proportion": {
                "idealTop": self.proportion.idealTop,
                "tolerance": self.proportion.tolerance,
            },
        }


def load_config(config_path: str | Path | None = None) -> ScoreConfig:
    """
    Load scoring configuration from JSON file.
    
    Args:
        config_path: Path to config file. If None, uses default location.
    
    Returns:
        ScoreConfig instance
    """
    if config_path is None:
        # Default: backend/config/scores-0.1.0.json
        config_path = Path(__file__).parent.parent / "config" / "scores-0.1.0.json"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        # Return default config if file doesn't exist
        return _default_config()
    
    with open(config_path, "r") as f:
        data = json.load(f)
    
    return ScoreConfig.from_dict(data)


def _default_config() -> ScoreConfig:
    """Return default configuration matching spec."""
    return ScoreConfig(
        version="scores-0.1.0",
        weights={
            "C": 0.25,  # Color Harmony
            "P": 0.15,  # Pattern Balance
            "T": 0.10,  # Texture Mix
            "H": 0.20,  # Highlight Principle
            "B": 0.20,  # Proportion
            "R": 0.10,  # Repetition
        },
        color=ColorConfig(dMin=8.0, dMax=35.0, tauH=10.0),
        pattern=PatternConfig(strong=0.6, mild=0.3),
        texture=TextureConfig(glossBonus=0.1),
        highlight=HighlightConfig(zThreshold=1.0),
        proportion=ProportionConfig(idealTop=0.33, tolerance=0.17),
    )

