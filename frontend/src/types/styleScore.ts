/**
 * TypeScript types for style scoring API
 * Matches backend scoring/types.py
 */

export type Material =
  | "denim"
  | "cotton"
  | "wool"
  | "knit"
  | "leather"
  | "satin"
  | "silk"
  | "synthetic";

export type PatternType =
  | "none"
  | "solid"
  | "stripe"
  | "plaid"
  | "graphic"
  | "floral"
  | "dots"
  | "other";

export type GarmentType = "top" | "bottom" | "outer" | "dress" | "accessory";

export interface GarmentFeatures {
  id: string;
  type: GarmentType;
  areaPct: number; // 0..1
  colorLAB: [number, number, number]; // [L, a, b]
  material: Material;
  patternType: PatternType;
  patternStrength: number; // 0..1
  glossIndex: number; // 0..1
}

export interface ColorCluster {
  lab: [number, number, number]; // [L, a, b]
  pct: number; // percentage (0..1)
}

export interface ThirdsArea {
  top: number;
  mid: number;
  bottom: number;
}

export interface DomainZ {
  skin: number;
  hue: number;
  texture: number;
  pattern: number;
}

export interface BodyMeasurements {
  waist?: number; // cm
  neck?: number; // cm
}

export interface OutfitFeatures {
  outfitId: string;
  garments: GarmentFeatures[];
  colorClusters: ColorCluster[]; // sorted desc by pct
  thirdsArea: ThirdsArea;
  domainZ: DomainZ;
  body?: BodyMeasurements | null;
  extractionVersion: string;
}

export interface StyleScoreSubscores {
  colorHarmony: number;
  patternBalance: number;
  textureMix: number;
  highlightPrinciple: number;
  proportion: number;
  repetition: number;
}

export interface StyleScore {
  version: string;
  styleScore: number; // 0..100
  subscores: StyleScoreSubscores;
  explanations: string[];
  debug?: Record<string, unknown> | null;
}

