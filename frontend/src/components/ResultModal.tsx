import { useCallback, useMemo, useState } from "react";
import Modal from "./Modal";
import PatternSection, { type PatternItem } from "./PatternSection";
import type { PatternResult, SegmentationPayload } from "../types/socket";
import { createOutfitFeatures } from "../utils/outfitFeatures";
import ScoreSection from "./ScoreSection";
import { useStyleScore } from "../hooks/useStyleScore";
import type { OutfitFeatures } from "../types/styleScore";

export default function ResultModal({
  open,
  onClose,
  items,
  patterns,
  seg,
}: {
  open: boolean;
  onClose: () => void;
  items: PatternItem[];
  patterns: PatternResult[];
  seg: SegmentationPayload | null;
}) {
  const [active, setActive] = useState<"analysis" | "score">("analysis");
  const [features, setFeatures] = useState<OutfitFeatures | null>(null);

  const patternsReady = useMemo(() => {
    if (items.length === 0) return false;
    return items.every((it) =>
      patterns.find((p) => p.id === it.id && p.pattern)
    );
  }, [items, patterns]);

  const handleTab = (t: "analysis" | "score") => {
    if (t === "score") {
      if (!seg || !patternsReady) return;
      if (!features) setFeatures(createOutfitFeatures(seg, patterns));
    }
    setActive(t);
  };

  const handleClose = useCallback(() => {
    setActive("analysis");
    setFeatures(null);

    onClose();
  }, [onClose]);

  const scoreFetcher = useStyleScore(features);

  return (
    <Modal open={open} title="Results" onClose={handleClose}>
      <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
        <button
          onClick={() => handleTab("analysis")}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            background: active === "analysis" ? "#111" : "#0a0a0a",
            border: "1px solid #222",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          Pattern Analysis
        </button>
        <button
          onClick={() => handleTab("score")}
          disabled={!patternsReady}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            background: active === "score" ? "#111" : "#0a0a0a",
            border: "1px solid #222",
            color: patternsReady ? "#fff" : "#666",
            cursor: patternsReady ? "pointer" : "not-allowed",
          }}
        >
          Style Score
        </button>
      </div>

      {active === "analysis" && <PatternSection items={items} />}

      {active === "score" && (
        <ScoreSection
          status={scoreFetcher.status}
          score={scoreFetcher.score}
          error={scoreFetcher.error}
        />
      )}
    </Modal>
  );
}
