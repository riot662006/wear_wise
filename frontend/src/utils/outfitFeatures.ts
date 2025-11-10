/**
 * Helper functions to transform current data into OutfitFeatures format
 * 
 * NOTE: This is a placeholder implementation. In production, you would
 * get colorClusters, thirdsArea, domainZ, etc. from your feature extraction pipeline.
 */

import type {
  OutfitFeatures,
  GarmentFeatures,
  ColorCluster,
  ThirdsArea,
  DomainZ,
} from "../types/styleScore";
import type { SegmentationPayload, PatternResult } from "../types/socket";

/**
 * Map pattern strings to PatternType
 */
function mapPatternType(pattern: string): OutfitFeatures["garments"][0]["patternType"] {
  const lower = pattern.toLowerCase();
  if (lower.includes("solid") || lower === "none") return "none";
  if (lower.includes("stripe")) return "stripe";
  if (lower.includes("plaid") || lower.includes("checked")) return "plaid";
  if (lower.includes("floral")) return "floral";
  if (lower.includes("dot") || lower.includes("polka")) return "dots";
  if (lower.includes("graphic")) return "graphic";
  return "other";
}

/**
 * Map label to garment type
 */
function mapGarmentType(label: string): OutfitFeatures["garments"][0]["type"] {
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

/**
 * Map label to material (heuristic)
 */
function mapMaterial(label: string): OutfitFeatures["garments"][0]["material"] {
  const lower = label.toLowerCase();
  if (lower.includes("denim") || lower.includes("jean")) return "denim";
  if (lower.includes("leather")) return "leather";
  if (lower.includes("wool")) return "wool";
  if (lower.includes("silk")) return "silk";
  if (lower.includes("satin")) return "satin";
  if (lower.includes("knit")) return "knit";
  return "cotton"; // default
}

/**
 * Generate mock color clusters from garments
 * In production, this would come from k-means clustering on the image
 */
function generateMockColorClusters(
  garments: GarmentFeatures[]
): ColorCluster[] {
  // Extract colors from garments and create clusters
  // This is a simplified version - real implementation would use k-means
  const colors = garments.map((g) => g.colorLAB);
  
  if (colors.length === 0) {
    return [
      { lab: [60, 0, 0], pct: 1.0 },
    ];
  }
  
  // Simple clustering: group similar colors
  const clusters: ColorCluster[] = [];
  const used = new Set<number>();
  
  for (let i = 0; i < Math.min(3, colors.length); i++) {
    if (used.has(i)) continue;
    
    const color = colors[i];
    let count = 1;
    used.add(i);
    
    // Find similar colors (simple distance check)
    for (let j = i + 1; j < colors.length; j++) {
      if (used.has(j)) continue;
      const dist = Math.sqrt(
        Math.pow(color[0] - colors[j][0], 2) +
        Math.pow(color[1] - colors[j][1], 2) +
        Math.pow(color[2] - colors[j][2], 2)
      );
      if (dist < 15) {
        count++;
        used.add(j);
      }
    }
    
    clusters.push({
      lab: color,
      pct: count / colors.length,
    });
  }
  
  // Sort by percentage descending
  clusters.sort((a, b) => b.pct - a.pct);
  
  // Normalize to sum to 1.0
  const total = clusters.reduce((sum, c) => sum + c.pct, 0);
  if (total > 0) {
    clusters.forEach((c) => (c.pct /= total));
  }
  
  // Ensure we have 3 clusters (pad if needed)
  while (clusters.length < 3) {
    clusters.push({
      lab: [50, 0, 0],
      pct: 0.0,
    });
  }
  
  return clusters.slice(0, 3);
}

/**
 * Generate mock thirds area
 * In production, this would come from person segmentation
 */
function generateMockThirdsArea(garments: GarmentFeatures[]): ThirdsArea {
  // Simple heuristic: top garments contribute to top third, bottom to bottom
  let top = 0;
  let bottom = 0;
  let mid = 0;
  
  garments.forEach((g) => {
    if (g.type === "top" || g.type === "outer") {
      top += g.areaPct;
    } else if (g.type === "bottom") {
      bottom += g.areaPct;
    } else {
      mid += g.areaPct;
    }
  });
  
  // Normalize
  const total = top + mid + bottom;
  if (total > 0) {
    top /= total;
    mid /= total;
    bottom /= total;
  } else {
    top = 0.33;
    mid = 0.34;
    bottom = 0.33;
  }
  
  return { top, mid, bottom };
}

/**
 * Generate mock domain z-scores
 * In production, this would come from feature extraction
 */
function generateMockDomainZ(garments: GarmentFeatures[]): DomainZ {
  // Simple heuristics:
  // - hue: based on color variance
  // - pattern: based on pattern strength
  // - texture: based on material variety
  // - skin: always low (we don't detect skin exposure)
  
  const patternStrengths = garments
    .filter((g) => g.patternType !== "none")
    .map((g) => g.patternStrength);
  
  const maxPatternStrength = patternStrengths.length > 0
    ? Math.max(...patternStrengths)
    : 0;
  
  const materials = new Set(garments.map((g) => g.material));
  const materialVariety = materials.size;
  
  // Calculate color variance
  const colors = garments.map((g) => g.colorLAB);
  const avgL = colors.reduce((sum, c) => sum + c[0], 0) / colors.length;
  const variance = colors.reduce(
    (sum, c) => sum + Math.pow(c[0] - avgL, 2),
    0
  ) / colors.length;
  
  return {
    skin: 0.2, // low (no skin detection)
    hue: Math.min(variance / 10, 2.0), // normalized variance
    texture: Math.min(materialVariety / 2, 2.0), // material count
    pattern: maxPatternStrength * 2, // pattern strength scaled
  };
}

/**
 * Transform segmentation and pattern data into OutfitFeatures
 * 
 * This is a placeholder that generates mock data for missing fields.
 * Replace with real feature extraction when available.
 */
export function createOutfitFeatures(
  seg: SegmentationPayload,
  patterns: PatternResult[],
  outfitId: string = `outfit-${Date.now()}`
): OutfitFeatures {
  // Create garments from segmentation + patterns
  const garments: GarmentFeatures[] = seg.items.map((item) => {
    const pattern = patterns.find((p) => p.id === item.id);
    const [x, y, w, h] = item.bbox;
    
    // Calculate area percentage (simplified - assumes full image area)
    const totalArea = seg.width * seg.height;
    const itemArea = w * h;
    const areaPct = totalArea > 0 ? itemArea / totalArea : 0.1;
    
    // Generate mock LAB color (in production, extract from image)
    // Simple heuristic: use a neutral color with slight variation
    const baseL = 60;
    const baseA = Math.sin(item.id.charCodeAt(0)) * 5;
    const baseB = Math.cos(item.id.charCodeAt(0)) * 5;
    const colorLAB: [number, number, number] = [
      baseL + Math.random() * 20 - 10,
      baseA,
      baseB,
    ];
    
    return {
      id: item.id,
      type: mapGarmentType(item.label),
      areaPct: Math.min(areaPct, 0.5), // cap at 50%
      colorLAB,
      material: mapMaterial(item.label),
      patternType: pattern
        ? mapPatternType(pattern.pattern)
        : "none",
      patternStrength: pattern?.confidence ?? 0.0,
      glossIndex: item.label.toLowerCase().includes("leather") ? 0.8 : 0.1,
    };
  });
  
  // Generate mock data for missing fields
  const colorClusters = generateMockColorClusters(garments);
  const thirdsArea = generateMockThirdsArea(garments);
  const domainZ = generateMockDomainZ(garments);
  
  return {
    outfitId,
    garments,
    colorClusters,
    thirdsArea,
    domainZ,
    body: null, // Optional - not available from current data
    extractionVersion: "mock-0.1.0", // Replace with real version
  };
}

