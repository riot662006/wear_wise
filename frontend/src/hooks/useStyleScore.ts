import { useState, useEffect } from "react";
import type { OutfitFeatures, StyleScore } from "../types/styleScore";
import { scoreOutfit } from "../api/styleScore";

export function useStyleScore(features: OutfitFeatures | null) {
  const [score, setScore] = useState<StyleScore | null>(null);
  const [status, setStatus] = useState<
    "idle" | "loading" | "error" | "success"
  >("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const MIN_DELAY = 500;

    const wait = (ms: number) => new Promise((res) => setTimeout(res, ms));

    (async () => {
      setStatus("loading");
      setScore(null);
      setError(null);

      if (!features) {
        setStatus("idle");
        return;
      }

      try {
        const [result] = await Promise.all([
          scoreOutfit(features), // gets the score
          wait(MIN_DELAY), // ensures minimum delay
        ]);

        if (cancelled) return;

        setScore(result);
        setStatus("success");
      } catch (err) {
        const error = err as Error;
        if (cancelled) return;

        setError(error?.message ?? String(error));
        setStatus("error");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [features]);

  return { score, status, error };
}
