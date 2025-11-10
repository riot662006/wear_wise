# Style Scoring System v0.1

Quantifiable, replicable, explainable style scores for WearWise outfits.

## Overview

The style scoring system computes a 0-100 style score based on six interpretable factors:

1. **Color Harmony (C)** - 50/30/20 color pyramid and hue harmony
2. **Pattern Balance (P)** - Rule of One for patterns
3. **Texture Mix (T)** - Material variety and gloss contrast
4. **Highlight Principle (H)** - Rule of One across domains
5. **Proportion (B)** - 33/66 visual ratio
6. **Repetition (R)** - Color echo between accent and accessories

## Quick Start

```python
from scoring import score_outfit, load_config, OutfitFeatures

# Load configuration
config = load_config()

# Prepare outfit features
features: OutfitFeatures = {
    "outfitId": "outfit-123",
    "garments": [...],  # List of GarmentFeatures
    "colorClusters": [...],  # Top 3 LAB color clusters
    "thirdsArea": {"top": 0.33, "mid": 0.34, "bottom": 0.33},
    "domainZ": {"skin": 0.2, "hue": 1.4, "texture": 0.5, "pattern": 0.1},
    "extractionVersion": "segm-1.2.0-kmeans-3",
    "body": None,  # Optional body measurements
}

# Score the outfit
result = score_outfit(features, config)

print(f"Style Score: {result['styleScore']:.1f}/100")
print("Subscores:", result['subscores'])
print("Explanations:", result['explanations'])
```

## API Endpoint

### POST `/api/style/score`

**Request Body:**
```json
{
  "outfitId": "abc123",
  "garments": [
    {
      "id": "top1",
      "type": "top",
      "areaPct": 0.31,
      "colorLAB": [62, -4, -8],
      "material": "cotton",
      "patternType": "plaid",
      "patternStrength": 0.72,
      "glossIndex": 0.1
    }
  ],
  "colorClusters": [
    {"lab": [60, -5, -7], "pct": 0.52},
    {"lab": [48, 2, 4], "pct": 0.30},
    {"lab": [70, -6, -10], "pct": 0.18}
  ],
  "thirdsArea": {"top": 0.35, "mid": 0.30, "bottom": 0.35},
  "domainZ": {"skin": 0.2, "hue": 1.4, "texture": 0.5, "pattern": 0.1},
  "extractionVersion": "segm-1.2.0-kmeans-3",
  "body": null
}
```

**Response:**
```json
{
  "version": "scores-0.1.0",
  "styleScore": 82.6,
  "subscores": {
    "colorHarmony": 0.84,
    "patternBalance": 1.0,
    "textureMix": 0.80,
    "highlightPrinciple": 0.95,
    "proportion": 0.65,
    "repetition": 0.90
  },
  "explanations": [
    "Color harmony is strong (close to 50/30/20).",
    "Single hero pattern detected; others kept calm."
  ],
  "debug": {...}
}
```

## Configuration

Configuration is stored in `backend/config/scores-0.1.0.json`:

```json
{
  "version": "scores-0.1.0",
  "weights": {
    "C": 0.25,  // Color Harmony
    "P": 0.15,  // Pattern Balance
    "T": 0.10,  // Texture Mix
    "H": 0.20,  // Highlight Principle
    "B": 0.20,  // Proportion
    "R": 0.10   // Repetition
  },
  "color": {
    "dMin": 8.0,   // Minimum CIEDE2000 distance (too close = muddy)
    "dMax": 35.0,  // Maximum CIEDE2000 distance (too far = clashing)
    "tauH": 10.0   // Temperature parameter for harmony penalty
  },
  "pattern": {
    "strong": 0.6,  // patternStrength >= this is "strong"
    "mild": 0.3     // patternStrength in [mild, strong) is "mild"
  },
  "texture": {
    "glossBonus": 0.1  // Bonus if exactly one glossy piece
  },
  "highlight": {
    "zThreshold": 1.0  // z-score threshold for "highlighted" domain
  },
  "proportion": {
    "idealTop": 0.33,    // Ideal top third ratio
    "tolerance": 0.17    // Tolerance around ideal
  }
}
```

## Algorithm Details

### Color Harmony (C)

- **Ratio Fit**: Measures how close the color distribution is to 50/30/20
- **Hue Harmony**: Uses CIEDE2000 distance to penalize muddy (too close) or clashing (too far) colors
- **Formula**: `C = 0.7 * ratio_fit + 0.3 * hue_harmony`

### Pattern Balance (P)

- **Rule of One**: One strong pattern (patternStrength >= 0.6) scores 1.0
- **Calm**: No strong patterns, ≤2 mild patterns scores 0.7
- **Penalty**: Multiple strong patterns reduce score

### Texture Mix (T)

- **Material Count**: Ideal is 2-3 unique materials
- **Gloss Bonus**: +0.1 if exactly one glossy piece (glossIndex >= 0.7)

### Highlight Principle (H)

- **Rule of One**: Exactly one domain with z-score ≥ 1.0 scores 1.0
- **Too Uniform**: No highlights scores 0.6
- **Penalty**: Multiple highlights reduce score

### Proportion (B)

- **Visual Ratio**: Measures top/bottom area ratio (ideal ~0.33)
- **Waist/Neck Echo**: Optional bonus for 0.2:1 waist/neck ratio

### Repetition (R)

- **Color Echo**: Rewards accessories within ΔE≤10 of accent color
- **Partial**: ΔE 10-18 scores 0.7
- **None**: Otherwise scores 0.3

## Testing

Run unit tests:

```bash
cd backend
python -m pytest tests/test_scoring.py -v
```

Run example:

```bash
cd backend
python -m scoring.example
```

## Determinism

The scoring system is deterministic:
- Same input always produces same output
- Fixed random seeds for k-means (handled upstream)
- All percentages rounded to 3 decimals
- All thresholds stored in versioned config

## Future Work

- Learn weights via ridge regression on human ratings
- Personalization: user-specific priors
- Seasonal appropriateness scores
- Multi-image robustness (front/side/back)

