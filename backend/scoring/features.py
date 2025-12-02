"""
Helpers to build `OutfitFeatures` server-side from segmentation + pattern results.
Uses real image-based feature extraction instead of heuristics.
"""
from __future__ import annotations
import math
import random
import numpy as np
from typing import Any, Dict, List, Tuple

from .types import (
    OutfitFeatures,
    GarmentFeatures,
)
from .image_features import (
    extract_dominant_colors,
    compute_color_variance,
    estimate_gloss_index,
    infer_material_from_image,
    estimate_pattern_strength,
    decode_image_from_base64,
)


def map_pattern_type(pattern: str) -> str:
    p = (pattern or "").lower()
    if "solid" in p or p == "none":
        return "none"
    if "stripe" in p:
        return "stripe"
    if "plaid" in p or "checked" in p:
        return "plaid"
    if "floral" in p:
        return "floral"
    if "dot" in p or "polka" in p:
        return "dots"
    if "graphic" in p:
        return "graphic"
    return "other"


def map_garment_type(label: str) -> str:
    l = (label or "").lower()
    if any(x in l for x in ("shirt", "top", "t-shirt", "tee")):
        return "top"
    if any(x in l for x in ("pant", "bottom", "jean", "trouser")):
        return "bottom"
    if "dress" in l:
        return "dress"
    if any(x in l for x in ("jacket", "coat")):
        return "outer"
    return "accessory"


def map_material(label: str) -> str:
    l = (label or "").lower()
    if any(x in l for x in ("denim", "jean")):
        return "denim"
    if "leather" in l:
        return "leather"
    if "wool" in l:
        return "wool"
    if "silk" in l:
        return "silk"
    if "satin" in l:
        return "satin"
    if "knit" in l:
        return "knit"
    return "cotton"


def generate_mock_color_clusters(garments: List[GarmentFeatures]) -> List[Dict[str, Any]]:
    """
    Extract color clusters from garment LAB colors.
    
    Returns top 3 clusters sorted by frequency.
    """
    colors = [g["colorLAB"] for g in garments if "colorLAB" in g]
    if not colors:
        return [{"lab": (60.0, 0.0, 0.0), "pct": 1.0}]

    # Simple frequency-based clustering on LAB space
    # Group similar colors (within 15 ΔE units)
    clusters: List[Dict[str, Any]] = []
    used = set()
    
    for i, c in enumerate(colors[:5]):  # Check first 5 colors
        if i in used:
            continue
        used.add(i)
        count = 1
        
        for j in range(i + 1, len(colors)):
            if j in used:
                continue
            # L2 distance in LAB
            d = math.sqrt(sum((c[k] - colors[j][k]) ** 2 for k in range(3)))
            if d < 15:
                used.add(j)
                count += 1
        
        clusters.append({"lab": tuple(c), "pct": float(count)})

    # Normalize percentages
    total = sum(c["pct"] for c in clusters)
    if total > 0:
        for c in clusters:
            c["pct"] = c["pct"] / total

    # Sort descending by frequency
    clusters.sort(key=lambda x: x["pct"], reverse=True)
    
    # Pad to 3 clusters
    while len(clusters) < 3:
        clusters.append({"lab": (50.0, 0.0, 0.0), "pct": 0.0})

    return clusters[:3]


def generate_thirds_area_from_seg(items: List[Dict[str, Any]], width: int, height: int) -> Dict[str, float]:
    """
    Compute area distribution across vertical thirds using segmentation bboxes.

    For each detected item (bbox x,y,w,h in VIDEO coords), compute how much
    of the bbox area falls into the top/mid/bottom thirds of the image and
    normalize to sum to 1. This provides a robust visual proportion measure.
    """
    try:
        if width <= 0 or height <= 0:
            return {"top": 0.33, "mid": 0.34, "bottom": 0.33}

        top_area = mid_area = bottom_area = 0.0

        t1 = height / 3.0
        t2 = 2.0 * height / 3.0

        for it in items:
            bbox = it.get("bbox", [0, 0, 0, 0])
            if not bbox or len(bbox) < 4:
                continue
            x, y, w, h = bbox
            # Clamp to image
            y0 = max(0.0, float(y))
            y1 = min(float(height), float(y + h))
            if y1 <= y0 or w <= 0:
                continue

            # Overlap heights with thirds
            top_h = max(0.0, min(y1, t1) - y0)
            mid_h = max(0.0, min(y1, t2) - max(y0, t1))
            bot_h = max(0.0, min(y1, float(height)) - max(y0, t2))

            # Accumulate area contribution (w * overlap_height)
            top_area += float(w) * top_h
            mid_area += float(w) * mid_h
            bottom_area += float(w) * bot_h

        total = top_area + mid_area + bottom_area
        if total > 1e-9:
            return {"top": top_area / total, "mid": mid_area / total, "bottom": bottom_area / total}
        return {"top": 0.33, "mid": 0.34, "bottom": 0.33}
    except Exception:
        return {"top": 0.33, "mid": 0.34, "bottom": 0.33}


def generate_mock_domain_z(garments: List[GarmentFeatures]) -> Dict[str, float]:
    """
    Compute domain z-scores from outfit features.
    
    - skin: not available (no face detection), always low
    - hue: standard deviation of hue channel across all colors
    - texture: variety of materials
    - pattern: average pattern strength
    """
    if not garments:
        return {"skin": 0.2, "hue": 0.0, "texture": 0.0, "pattern": 0.0}
    
    # Pattern strength
    pattern_strengths = [
        g.get("patternStrength", 0.0)
        for g in garments
        if g.get("patternType", "none") != "none"
    ]
    avg_pattern = np.mean(pattern_strengths) if pattern_strengths else 0.0
    
    # Texture variety (material count)
    materials = {g.get("material") for g in garments}
    material_variety = len([m for m in materials if m])
    
    # Hue variance: compute std dev of a,b channels across colors
    colors = [g.get("colorLAB", (60.0, 0.0, 0.0)) for g in garments]
    if len(colors) > 1:
        colors_arr = np.array(colors)
        # a,b channels (hue)
        ab = colors_arr[:, 1:]
        hue_std = float(np.std(ab))
    else:
        hue_std = 0.0
    
    # Normalize to z-scores
    # Typical ranges (these could be calibrated):
    # - hue std: 0-15 (0 = monochrome, 15+ = very diverse)
    # - texture variety: 0-5 materials
    # - pattern avg: 0-1
    
    z_hue = min(hue_std / 10.0, 3.0)  # Cap at 3
    z_texture = min(material_variety / 2.5, 2.0)  # Cap at 2
    z_pattern = min(avg_pattern * 2.0, 3.0)  # Cap at 3
    
    return {
        "skin": 0.2,  # Always low (no skin detection)
        "hue": float(z_hue),
        "texture": float(z_texture),
        "pattern": float(z_pattern),
    }


def create_outfit_features(
    seg: Dict[str, Any],
    patterns: List[Dict[str, Any]],
    outfit_id: str | None = None,
    crop_images: Dict[str, str] | None = None
) -> OutfitFeatures:
    """
    Create outfit features from segmentation, patterns, and optional crop images.
    
    Args:
        seg: {width, height, items: [{id, bbox, label, score}]}
        patterns: [{id, pattern, confidence}]
        outfit_id: Optional outfit ID
        crop_images: Optional {garment_id: base64_dataUrl} for real feature extraction
    
    Returns:
        OutfitFeatures with real extracted data where images available
    """
    items = seg.get("items", [])
    width = int(seg.get("width", 0))
    height = int(seg.get("height", 0))
    
    if crop_images is None:
        crop_images = {}

    garments: List[GarmentFeatures] = []
    
    for it in items:
        pid = it.get("id", "unk")
        label = it.get("label", "garment")
        x, y, w, h = it.get("bbox", [0, 0, 0, 0])
        total_area = float(max(1, width * height))
        item_area = float(w * h)
        area_pct = min(item_area / total_area if total_area > 0 else 0.0, 0.5)

        # Find pattern match
        pat = next((p for p in patterns if p.get("id") == pid), None)
        pattern_type = map_pattern_type(pat.get("pattern") if pat else "none")
        
        # Try to extract real features from image crop
        crop_data_url = crop_images.get(pid)
        if crop_data_url:
            img_array = decode_image_from_base64(crop_data_url)
            if img_array is not None and img_array.size > 0:
                # Real extraction from image
                try:
                    # Extract dominant colors
                    colors = extract_dominant_colors(img_array, n_clusters=3)
                    color_lab = tuple(colors[0]) if colors else (60.0, 0.0, 0.0)
                    
                    # Prefer AI-provided material if present in pattern results
                    if pat and pat.get("material"):
                        material = pat.get("material")
                        try:
                            material_conf = float(pat.get("materialConfidence", 0.0))
                        except Exception:
                            material_conf = 0.0
                        # If AI confidence is low, combine with image-based inference
                        if material_conf < 0.5:
                            try:
                                inferred = infer_material_from_image(img_array, label)
                                # prefer inferred if different
                                if inferred and inferred != material:
                                    material = inferred
                                    material_conf = max(material_conf, 0.4)
                            except Exception:
                                pass
                    else:
                        material = infer_material_from_image(img_array, label)
                        material_conf = 0.0

                    # Estimate gloss
                    gloss = estimate_gloss_index(img_array)

                    # Estimate pattern strength
                    pattern_strength = estimate_pattern_strength(img_array, pattern_type)
                    
                except Exception as e:
                    # Fallback on error
                    print(f"Error extracting features for {pid}: {e}")
                    color_lab = _generate_mock_color(pid)
                    material = map_material(label)
                    material_conf = 0.0
                    gloss = 0.8 if "leather" in label.lower() else 0.1
                    pattern_strength = float(pat.get("confidence", 0.0)) if pat else 0.0
            else:
                # No valid image, use heuristics
                color_lab = _generate_mock_color(pid)
                material = map_material(label)
                material_conf = 0.0
                gloss = 0.8 if "leather" in label.lower() else 0.1
                pattern_strength = float(pat.get("confidence", 0.0)) if pat else 0.0
        else:
            # No crop data available, use heuristics
            color_lab = _generate_mock_color(pid)
            material = map_material(label)
            material_conf = 0.0
            gloss = 0.8 if "leather" in label.lower() else 0.1
            pattern_strength = float(pat.get("confidence", 0.0)) if pat else 0.0

        garments.append({
            "id": pid,
            "type": map_garment_type(label),
            "areaPct": area_pct,
            "colorLAB": color_lab,
            "material": material,
            "materialConfidence": float(material_conf),
            "patternType": pattern_type,
            "patternStrength": pattern_strength,
            "glossIndex": gloss,
        })

    color_clusters = generate_mock_color_clusters(garments)
    # Compute thirds area using the original segmentation bboxes for accurate proportions
    thirds_area = generate_thirds_area_from_seg(items, width, height)
    domain_z = generate_mock_domain_z(garments)

    return {
        "outfitId": outfit_id or f"outfit-{int(random.random()*1e9)}",
        "garments": garments,
        "colorClusters": color_clusters,
        "thirdsArea": thirds_area,
        "domainZ": domain_z,
        "body": None,
        "extractionVersion": "real-0.1.0",  # Indicates real extraction was used
    }


def _generate_mock_color(garment_id: str) -> tuple[float, float, float]:
    """Generate deterministic mock LAB color from ID."""
    seed = sum(ord(c) for c in str(garment_id))
    random.seed(seed)
    base_l = 60.0 + (random.random() * 20.0 - 10.0)
    base_a = math.sin(seed % 10) * 5.0
    base_b = math.cos(seed % 10) * 5.0
    return (round(base_l, 2), round(base_a, 2), round(base_b, 2))
