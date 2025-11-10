/**
 * API functions for style scoring
 */

import type { OutfitFeatures, StyleScore } from "../types/styleScore";

const API_BASE_URL = "http://localhost:5000";

/**
 * Score an outfit using the style scoring API
 */
export async function scoreOutfit(
  features: OutfitFeatures
): Promise<StyleScore> {
  const response = await fetch(`${API_BASE_URL}/api/style/score`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(features),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

