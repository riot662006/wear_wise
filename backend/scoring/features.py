"""
Helpers to build `OutfitFeatures` server-side from segmentation + pattern results.
This is a Python port of the frontend `createOutfitFeatures` helper used for
quick integration while a production extraction pipeline is developed.
"""
from __future__ import annotations
import math
import random
from typing import Any, Dict, List, Tuple

from .types import (
    OutfitFeatures,
    GarmentFeatures,
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
    # Very small heuristic clustering: use garment colors as seed clusters
    colors = [g["colorLAB"] for g in garments if "colorLAB" in g]
    if not colors:
        return [{"lab": (60.0, 0.0, 0.0), "pct": 1.0}]

    clusters: List[Dict[str, Any]] = []
    used = set()
    for i, c in enumerate(colors[:3]):
        if i in used:
            continue
        used.add(i)
        count = 1
        for j in range(i + 1, len(colors)):
            if j in used:
                continue
            # simple L2 distance in LAB
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

    # Pad to 3 clusters
    while len(clusters) < 3:
        clusters.append({"lab": (50.0, 0.0, 0.0), "pct": 0.0})

    # sort desc
    clusters.sort(key=lambda x: x["pct"], reverse=True)
    return clusters[:3]


def generate_mock_thirds_area(garments: List[GarmentFeatures], width: int, height: int) -> Dict[str, float]:
    top = bottom = mid = 0.0
    total_area = float(max(1, width * height))
    for g in garments:
        area_pct = float(g.get("areaPct", 0.0))
        if g.get("type") in ("top", "outer"):
            top += area_pct
        elif g.get("type") == "bottom":
            bottom += area_pct
        else:
            mid += area_pct

    total = top + mid + bottom
    if total > 0:
        return {"top": top / total, "mid": mid / total, "bottom": bottom / total}
    return {"top": 0.33, "mid": 0.34, "bottom": 0.33}


def generate_mock_domain_z(garments: List[GarmentFeatures]) -> Dict[str, float]:
    # Simple heuristics mirroring the frontend helper
    pattern_strengths = [g.get("patternStrength", 0.0) for g in garments if g.get("patternType", "none") != "none"]
    max_pattern = max(pattern_strengths) if pattern_strengths else 0.0
    materials = {g.get("material") for g in garments}
    material_variety = len([m for m in materials if m])

    # color variance on L channel
    colors = [g.get("colorLAB", (60.0, 0.0, 0.0)) for g in garments]
    if colors:
        avg_l = sum(c[0] for c in colors) / len(colors)
        variance = sum((c[0] - avg_l) ** 2 for c in colors) / len(colors)
    else:
        variance = 0.0

    return {
        "skin": 0.2,
        "hue": min(variance / 10.0, 2.0),
        "texture": min(material_variety / 2.0, 2.0),
        "pattern": max_pattern * 2.0,
    }


def create_outfit_features(seg: Dict[str, Any], patterns: List[Dict[str, Any]], outfit_id: str | None = None) -> OutfitFeatures:
    # seg: { width, height, items: [{id, bbox:[x,y,w,h], label, score}] }
    items = seg.get("items", [])
    width = int(seg.get("width", 0))
    height = int(seg.get("height", 0))

    garments: List[GarmentFeatures] = []
    for it in items:
        pid = it.get("id", "unk")
        label = it.get("label", "garment")
        x, y, w, h = it.get("bbox", [0, 0, 0, 0])
        total_area = float(max(1, width * height))
        item_area = float(w * h)
        area_pct = min(item_area / total_area if total_area > 0 else 0.0, 0.5)

        # find pattern match
        pat = next((p for p in patterns if p.get("id") == pid), None)

        # deterministic-ish mock color based on id
        seed = sum(ord(c) for c in str(pid))
        random.seed(seed)
        base_l = 60.0 + (random.random() * 20.0 - 10.0)
        base_a = math.sin(seed % 10) * 5.0
        base_b = math.cos(seed % 10) * 5.0
        color_lab = (round(base_l, 2), round(base_a, 2), round(base_b, 2))

        garments.append({
            "id": pid,
            "type": map_garment_type(label),
            "areaPct": area_pct,
            "colorLAB": color_lab,
            "material": map_material(label),
            "patternType": map_pattern_type(pat.get("pattern") if pat else "none"),
            "patternStrength": float(pat.get("confidence", 0.0)) if pat else 0.0,
            "glossIndex": 0.8 if "leather" in (label or "").lower() else 0.1,
        })

    color_clusters = generate_mock_color_clusters(garments)
    thirds_area = generate_mock_thirds_area(garments, width, height)
    domain_z = generate_mock_domain_z(garments)

    return {
        "outfitId": outfit_id or f"outfit-{int(random.random()*1e9)}",
        "garments": garments,
        "colorClusters": color_clusters,
        "thirdsArea": thirds_area,
        "domainZ": domain_z,
        "body": None,
        "extractionVersion": "mock-0.1.0",
    }
