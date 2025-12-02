/**
 * Transform segmentation and pattern data into OutfitFeatures.
 * Calls backend API to extract real features from garment crop images.
 */

import type { OutfitFeatures } from "../types/styleScore";
import type { SegmentationPayload, PatternResult } from "../types/socket";

const API_BASE_URL = "http://localhost:5000";

interface ExtractResponse {
  features: OutfitFeatures;
  profiling?: { extraction_ms: number };
}

/**
 * Transform segmentation and pattern data into OutfitFeatures using backend API.
 *
 * This function calls the backend feature extraction endpoint, which uses
 * real image analysis (k-means color clustering, gloss detection, material inference)
 * instead of heuristics.
 *
 * @param seg - Segmentation payload with detection results
 * @param patterns - Pattern detection results for each garment
 * @param outfitId - Optional outfit ID
 * @param cropDataUrls - Optional map of {garmentId: base64ImageDataUrl}
 * @returns OutfitFeatures with real extracted features
 */
export async function createOutfitFeatures(
  seg: SegmentationPayload,
  patterns: PatternResult[],
  outfitId: string = `outfit-${Date.now()}`,
  cropDataUrls?: Record<string, string>
): Promise<OutfitFeatures> {
  try {
    // Prepare the request payload
    const payload = {
      segmentation: seg,
      patterns: patterns,
      outfitId: outfitId,
      cropImages: cropDataUrls || {},
      profile: false,
    };

    // Call backend feature extraction endpoint
    const response = await fetch(`${API_BASE_URL}/api/extract/features`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ error: "Unknown error" }));
      throw new Error(
        error.error || `HTTP ${response.status}: ${response.statusText}`
      );
    }

    const data: ExtractResponse = await response.json();
    return data.features;
  } catch (error) {
    console.error("Feature extraction failed:", error);
    // Fallback to basic features if extraction fails
    return createFallbackFeatures(seg, patterns, outfitId);
  }
}

/**
 * Fallback feature creation when API call fails.
 * Uses simple heuristics instead of real image analysis.
 */
function createFallbackFeatures(
  seg: SegmentationPayload,
  patterns: PatternResult[],
  outfitId: string
): OutfitFeatures {
  const garments = seg.items.map((item) => {
    const pattern = patterns.find((p) => p.id === item.id);
    const [, , w, h] = item.bbox;

    const totalArea = seg.width * seg.height;
    const itemArea = w * h;
    const areaPct = totalArea > 0 ? itemArea / totalArea : 0.1;

    // Generate deterministic LAB color from ID
    const seed = item.id.charCodeAt(0);
    const baseL = 60 + Math.sin(seed) * 20;
    const baseA = Math.cos(seed) * 5;
    const baseB = Math.sin(seed * 2) * 5;

    const garmentType = mapGarmentType(item.label);
    const material = mapMaterial(item.label);
    const patternType = pattern ? mapPatternType(pattern.pattern) : "none";

    return {
      id: item.id,
      type: garmentType as OutfitFeatures["garments"][0]["type"],
      areaPct: Math.min(areaPct, 0.5),
      colorLAB: [baseL, baseA, baseB] as [number, number, number],
      material: material as OutfitFeatures["garments"][0]["material"],
      patternType: patternType as OutfitFeatures["garments"][0]["patternType"],
      patternStrength: pattern?.confidence ?? 0.0,
      glossIndex: item.label.toLowerCase().includes("leather") ? 0.8 : 0.1,
    };
  });

  // Generate basic color clusters
  const colorClusters = garments.slice(0, 3).map((g, i) => ({
    lab: g.colorLAB,
    pct: i === 0 ? 0.5 : i === 1 ? 0.3 : 0.2,
  }));

  // Generate thirds area
  let top = 0,
    bottom = 0,
    mid = 0;
  garments.forEach((g) => {
    if (g.type === "top" || g.type === "outer") top += g.areaPct;
    else if (g.type === "bottom") bottom += g.areaPct;
    else mid += g.areaPct;
  });
  const total = top + mid + bottom;
  const thirdsArea = {
    top: total > 0 ? top / total : 0.33,
    mid: total > 0 ? mid / total : 0.34,
    bottom: total > 0 ? bottom / total : 0.33,
  };

  // Generate domain z-scores
  const materials = new Set(garments.map((g) => g.material));
  const domainZ = {
    skin: 0.2,
    hue: 0.5,
    texture: Math.min(materials.size / 2.5, 2.0),
    pattern: Math.max(...garments.map((g) => g.patternStrength)) * 2.0,
  };

  return {
    outfitId,
    garments,
    colorClusters,
    thirdsArea,
    domainZ,
    body: null,
    extractionVersion: "fallback-0.1.0",
  };
}

function mapPatternType(pattern: string): string {
  const lower = pattern.toLowerCase();
  if (lower.includes("solid") || lower === "none") return "none";
  if (lower.includes("stripe")) return "stripe";
  if (lower.includes("plaid") || lower.includes("checked")) return "plaid";
  if (lower.includes("floral")) return "floral";
  if (lower.includes("dot") || lower.includes("polka")) return "dots";
  if (lower.includes("graphic")) return "graphic";
  return "other";
}

function mapGarmentType(label: string): string {
  const lower = label.toLowerCase();
  if (lower.includes("shirt") || lower.includes("top") || lower.includes("t-shirt")) {
    return "top";
  }
  if (lower.includes("pant") || lower.includes("bottom") || lower.includes("jean")) {
    return "bottom";
  }
  if (lower.includes("dress")) return "dress";
  if (lower.includes("jacket") || lower.includes("coat")) return "outer";
  return "accessory";
}

function mapMaterial(label: string): string {
  const lower = label.toLowerCase();
  if (lower.includes("denim") || lower.includes("jean")) return "denim";
  if (lower.includes("leather")) return "leather";
  if (lower.includes("wool")) return "wool";
  if (lower.includes("silk")) return "silk";
  if (lower.includes("satin")) return "satin";
  if (lower.includes("knit")) return "knit";
  return "cotton";
}
