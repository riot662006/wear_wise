"""
Main style scoring algorithm implementation.
"""

from __future__ import annotations
import math
from typing import Any

from .types import OutfitFeatures, StyleScore
from .config import ScoreConfig
from .color_distance import delta_e_00


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


def score_color_harmony(
    color_clusters: list[dict[str, Any]],
    cfg: ScoreConfig
) -> tuple[float, dict[str, Any]]:
    """
    Compute Color Harmony subscore (C).
    
    Implements 50/30/20 pyramid and hue harmony via CIEDE2000.
    
    Returns:
        (score, debug_info)
    """
    # Extract percentages (should be sorted desc)
    p = [c["pct"] for c in color_clusters[:3]]
    # Pad if less than 3 clusters
    while len(p) < 3:
        p.append(0.0)
    p = p[:3]
    
    # Normalize to sum to 1
    total = sum(p)
    if total > 0:
        p = [pi / total for pi in p]
    else:
        p = [0.5, 0.3, 0.2]  # fallback
    
    # Ideal vector
    q = [0.50, 0.30, 0.20]
    
    # Ratio fit: r = 1 - 0.5 * sum(|pi - qi|)
    r = 1.0 - 0.5 * sum(abs(pi - qi) for pi, qi in zip(p, q))
    r = clamp(r, 0.0, 1.0)
    
    # Hue harmony: average pairwise CIEDE2000 distance
    if len(color_clusters) >= 3:
        d01 = delta_e_00(color_clusters[0]["lab"], color_clusters[1]["lab"])
        d02 = delta_e_00(color_clusters[0]["lab"], color_clusters[2]["lab"])
        d12 = delta_e_00(color_clusters[1]["lab"], color_clusters[2]["lab"])
        dbar = (d01 + d02 + d12) / 3.0
    elif len(color_clusters) == 2:
        dbar = delta_e_00(color_clusters[0]["lab"], color_clusters[1]["lab"])
    else:
        dbar = 0.0  # single color, no harmony to measure
    
    # Harmony penalty: penalize if too close (muddy) or too far (clashing)
    d_min = cfg.color.dMin
    d_max = cfg.color.dMax
    tau_h = cfg.color.tauH
    
    h = (math.exp(-max(0.0, dbar - d_max) / tau_h) *
         math.exp(-max(0.0, d_min - dbar) / tau_h))
    h = clamp(h, 0.0, 1.0)
    
    # Final: C = 0.7*r + 0.3*h
    C = 0.7 * r + 0.3 * h
    C = clamp(C, 0.0, 1.0)
    
    debug = {"p": [round(pi, 3) for pi in p], "dbar": round(dbar, 2), "r": round(r, 3), "h": round(h, 3)}
    
    return C, debug


def score_pattern_balance(
    garments: list[dict[str, Any]],
    cfg: ScoreConfig
) -> tuple[float, dict[str, Any]]:
    """
    Compute Pattern Balance subscore (P).
    
    Implements Rule of One for patterns.
    
    Returns:
        (score, debug_info)
    """
    # Filter out "none" patterns
    strengths = [
        g["patternStrength"]
        for g in garments
        if g.get("patternType", "none") != "none"
    ]
    
    strong = sum(1 for s in strengths if s >= cfg.pattern.strong)
    mild = sum(1 for s in strengths if cfg.pattern.mild <= s < cfg.pattern.strong)
    
    if strong == 1 and mild == 0:
        P = 1.0
    elif strong == 0 and mild <= 2:
        P = 0.7
    else:
        P = max(0.0, 1.0 - 0.25 * (strong - 1) - 0.15 * mild)
    
    P = clamp(P, 0.0, 1.0)
    
    debug = {"strong": strong, "mild": mild, "total_patterns": len(strengths)}
    
    return P, debug


def score_texture_mix(
    garments: list[dict[str, Any]],
    cfg: ScoreConfig
) -> tuple[float, dict[str, Any]]:
    """
    Compute Texture Mix subscore (T).
    
    Rewards 2-3 unique materials; bonus for single glossy piece.
    
    Returns:
        (score, debug_info)
    """
    materials = {g["material"] for g in garments}
    m = len(materials)
    
    # Base score: peaks near 2-3 materials
    Tb = 1.0 - min(abs(m - 2.5), 2.0) / 2.0
    Tb = clamp(Tb, 0.0, 1.0)
    
    # Gloss contrast bonus: exactly one glossy piece
    glossy = sum(1 for g in garments if g.get("glossIndex", 0.0) >= 0.7)
    T = min(1.0, Tb + (cfg.texture.glossBonus if glossy == 1 else 0.0))
    
    debug = {"materials": list(materials), "m": m, "glossy": glossy}
    
    return T, debug


def score_highlight_principle(
    domain_z: dict[str, float],
    cfg: ScoreConfig
) -> tuple[float, dict[str, Any]]:
    """
    Compute Highlight Principle subscore (H).
    
    Implements Rule of One across four domains.
    
    Returns:
        (score, debug_info)
    """
    zs = domain_z
    k = sum(1 for v in zs.values() if v >= cfg.highlight.zThreshold)
    
    if k == 1:
        H = 1.0
    elif k == 0:
        H = 0.6
    else:
        H = max(0.0, 1.0 - 0.25 * (k - 1))
    
    H = clamp(H, 0.0, 1.0)
    
    debug = {"k": k, "zs": {k: round(v, 2) for k, v in zs.items()}}
    
    return H, debug


def score_proportion(
    thirds_area: dict[str, float],
    body: dict[str, Any] | None,
    cfg: ScoreConfig
) -> tuple[float, dict[str, Any]]:
    """
    Compute Proportion subscore (B).
    
    Implements 33/66 visual ratio and optional waist/neck echo.
    
    Returns:
        (score, debug_info)
    """
    top = thirds_area.get("top", 0.0)
    bottom = thirds_area.get("bottom", 0.0)
    
    total = top + bottom
    if total < 1e-6:
        rho = cfg.proportion.idealTop
    else:
        rho = top / total
    
    # B1: ratio fit
    B1 = 1.0 - min(abs(rho - cfg.proportion.idealTop) / cfg.proportion.tolerance, 1.0)
    B1 = clamp(B1, 0.0, 1.0)
    
    # B2: waist/neck echo (optional)
    if body and body.get("waist") and body.get("neck"):
        waist = float(body["waist"])
        neck = float(body["neck"])
        if neck > 0:
            wn = waist / neck
            B2 = math.exp(-abs(wn - 0.2) / 0.1)
            B2 = clamp(B2, 0.0, 1.0)
            B = 0.8 * B1 + 0.2 * B2
        else:
            B = B1
    else:
        B = B1
    
    B = clamp(B, 0.0, 1.0)
    
    debug = {"rho": round(rho, 3), "B1": round(B1, 3)}
    if body and body.get("waist") and body.get("neck"):
        debug["wn"] = round(body["waist"] / body["neck"], 3)
        debug["B2"] = round(B2, 3) if 'B2' in locals() else None
    
    return B, debug


def score_repetition(
    garments: list[dict[str, Any]],
    color_clusters: list[dict[str, Any]]
) -> tuple[float, dict[str, Any]]:
    """
    Compute Repetition/Echo subscore (R).
    
    Rewards color echo between accent and accessories.
    
    Returns:
        (score, debug_info)
    """
    if len(color_clusters) < 2:
        return 0.3, {"reason": "insufficient_clusters"}
    
    # Treat cluster 1 (second largest) as accent
    accent_lab = color_clusters[1]["lab"]
    
    # Check accessories/secondary pieces
    deltas = []
    accessory_types = ("accessory", "shoes", "hat", "bag", "outer")
    
    for g in garments:
        if g.get("type") in accessory_types:
            delta = delta_e_00(g["colorLAB"], accent_lab)
            deltas.append(delta)
    
    if not deltas:
        return 0.3, {"reason": "no_accessories"}
    
    min_delta = min(deltas)
    
    if min_delta <= 10:
        R = 1.0
    elif min_delta <= 18:
        R = 0.7
    else:
        R = 0.3
    
    debug = {"min_delta": round(min_delta, 2), "deltas": [round(d, 2) for d in deltas[:5]]}
    
    return R, debug


def explain_subscores(
    C: float, P: float, T: float, H: float, B: float, R: float
) -> list[str]:
    """
    Generate human-readable explanations for subscores.
    
    Returns:
        List of explanation strings
    """
    msgs = []
    
    if C >= 0.8:
        msgs.append("Color harmony is strong (close to 50/30/20).")
    elif C < 0.5:
        msgs.append("Color ratios deviate from 50/30/20; consider reducing extra accent.")
    
    if P == 1.0:
        msgs.append("Single hero pattern detected; others kept calm.")
    elif P < 0.5:
        msgs.append("Multiple strong patterns compete; consider simplifying.")
    
    if T >= 0.8:
        msgs.append("Good texture variety without clutter.")
    elif T < 0.5:
        msgs.append("Texture mix could be improved; aim for 2-3 distinct materials.")
    
    if H >= 0.9:
        msgs.append("Clear focal point following the Rule of One.")
    elif H < 0.6:
        msgs.append("Outfit lacks a clear highlight; consider emphasizing one element.")
    
    if B >= 0.8:
        msgs.append("Proportions are well-balanced.")
    elif B < 0.6:
        msgs.append("Outfit looks top/bottom heavy; aim near a 33/66 split.")
    
    if R >= 0.9:
        msgs.append("Nice color echo between accent and accessories.")
    elif R < 0.5:
        msgs.append("Consider adding color repetition between accent and accessories.")
    
    # If no specific messages, add a general one
    if not msgs:
        msgs.append("Outfit shows balanced style elements.")
    
    return msgs


def score_outfit(features: OutfitFeatures, cfg: ScoreConfig | None = None) -> StyleScore:
    """
    Compute complete style score for an outfit.
    
    Args:
        features: OutfitFeatures dictionary
        cfg: ScoreConfig (if None, loads default)
    
    Returns:
        StyleScore dictionary
    """
    from .config import load_config
    
    if cfg is None:
        cfg = load_config()
    
    # Ensure color clusters are sorted by pct desc
    clusters = sorted(
        features["colorClusters"],
        key=lambda c: c["pct"],
        reverse=True
    )
    
    # Compute subscores
    C, debug_c = score_color_harmony(clusters, cfg)
    P, debug_p = score_pattern_balance(features["garments"], cfg)
    T, debug_t = score_texture_mix(features["garments"], cfg)
    H, debug_h = score_highlight_principle(features["domainZ"], cfg)
    B, debug_b = score_proportion(features["thirdsArea"], features.get("body"), cfg)
    R, debug_r = score_repetition(features["garments"], clusters)
    
    # Final weighted score
    W = cfg.weights
    S = 100.0 * (
        W["C"] * C +
        W["P"] * P +
        W["T"] * T +
        W["H"] * H +
        W["B"] * B +
        W["R"] * R
    )
    
    # Round subscores to 3 decimals, final score to 1 decimal
    subscores = {
        "colorHarmony": round(C, 3),
        "patternBalance": round(P, 3),
        "textureMix": round(T, 3),
        "highlightPrinciple": round(H, 3),
        "proportion": round(B, 3),
        "repetition": round(R, 3),
    }
    
    # Generate explanations
    explanations = explain_subscores(C, P, T, H, B, R)
    
    # Debug info
    debug = {
        "color": debug_c,
        "pattern": debug_p,
        "texture": debug_t,
        "highlight": debug_h,
        "proportion": debug_b,
        "repetition": debug_r,
    }
    
    return {
        "version": cfg.version,
        "styleScore": round(S, 1),
        "subscores": subscores,
        "explanations": explanations,
        "debug": debug,
    }

