import { useState, useEffect } from "react";
import Modal from "./Modal";
import type { StyleScore } from "../types/styleScore";

export default function StyleScoreModal({
  open,
  onClose,
  features,
}: {
  open: boolean;
  onClose: () => void;
  features: any; // OutfitFeatures or null
}) {
  const [score, setScore] = useState<StyleScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && features) {
      setLoading(true);
      setError(null);
      setScore(null);

      // Import dynamically to avoid issues
      import("../api/styleScore")
        .then(({ scoreOutfit }) => scoreOutfit(features))
        .then((result) => {
          setScore(result);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message || "Failed to score outfit");
          setLoading(false);
        });
    } else if (!open) {
      // Reset when modal closes
      setScore(null);
      setError(null);
      setLoading(false);
    }
  }, [open, features]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return "#4ade80"; // green
    if (score >= 60) return "#fbbf24"; // yellow
    return "#f87171"; // red
  };

  const getSubscoreColor = (subscore: number) => {
    if (subscore >= 0.8) return "#4ade80";
    if (subscore >= 0.6) return "#fbbf24";
    return "#f87171";
  };

  return (
    <Modal open={open} title="Style Score" onClose={onClose}>
      {!features ? (
        <div style={{ color: "#aaa", textAlign: "center", padding: 20 }}>
          No outfit data available. Please analyze patterns first.
        </div>
      ) : loading ? (
        <div
          style={{
            display: "grid",
            placeItems: "center",
            padding: 40,
            color: "#aaa",
          }}
        >
          <div
            aria-label="loading"
            style={{
              width: 40,
              height: 40,
              border: "4px solid rgba(255,255,255,0.2)",
              borderTopColor: "white",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
            }}
          />
          <div style={{ marginTop: 16 }}>Calculating style score...</div>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      ) : error ? (
        <div
          style={{
            padding: 20,
            background: "#1a1a1a",
            borderRadius: 8,
            border: "1px solid #ff6b6b",
            color: "#ff6b6b",
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Error</div>
          <div>{error}</div>
        </div>
      ) : score ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Main Score */}
          <div
            style={{
              textAlign: "center",
              padding: 24,
              background: "#0f0f0f",
              borderRadius: 12,
              border: "1px solid #2a2a2a",
            }}
          >
            <div
              style={{
                fontSize: 48,
                fontWeight: 700,
                color: getScoreColor(score.styleScore),
                marginBottom: 8,
              }}
            >
              {score.styleScore.toFixed(1)}
            </div>
            <div style={{ color: "#aaa", fontSize: 14 }}>Style Score / 100</div>
            <div style={{ color: "#666", fontSize: 12, marginTop: 4 }}>
              v{score.version}
            </div>
          </div>

          {/* Subscores */}
          <div>
            <div
              style={{
                fontWeight: 600,
                marginBottom: 12,
                fontSize: 16,
                color: "#fff",
              }}
            >
              Subscores
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                gap: 12,
              }}
            >
              {Object.entries(score.subscores).map(([key, value]) => (
                <div
                  key={key}
                  style={{
                    padding: 12,
                    background: "#0f0f0f",
                    borderRadius: 8,
                    border: "1px solid #2a2a2a",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color: "#aaa",
                      marginBottom: 4,
                      textTransform: "capitalize",
                    }}
                  >
                    {key.replace(/([A-Z])/g, " $1").trim()}
                  </div>
                  <div
                    style={{
                      fontSize: 20,
                      fontWeight: 600,
                      color: getSubscoreColor(value),
                    }}
                  >
                    {(value * 100).toFixed(0)}%
                  </div>
                  <div
                    style={{
                      width: "100%",
                      height: 4,
                      background: "#1a1a1a",
                      borderRadius: 2,
                      marginTop: 6,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${value * 100}%`,
                        height: "100%",
                        background: getSubscoreColor(value),
                        transition: "width 0.3s ease",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Explanations */}
          {score.explanations.length > 0 && (
            <div>
              <div
                style={{
                  fontWeight: 600,
                  marginBottom: 12,
                  fontSize: 16,
                  color: "#fff",
                }}
              >
                Insights
              </div>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                {score.explanations.map((explanation, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: 12,
                      background: "#0f0f0f",
                      borderRadius: 8,
                      border: "1px solid #2a2a2a",
                      color: "#ddd",
                      fontSize: 14,
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 8,
                    }}
                  >
                    <span style={{ color: "#8ef", marginTop: 2 }}>•</span>
                    <span>{explanation}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : null}
    </Modal>
  );
}

