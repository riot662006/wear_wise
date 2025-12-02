import React from "react";
import type { StyleScore } from "../types/styleScore";

const ScoreSection = React.memo(ScoreSectionInner);

function ScoreSectionInner({
  score,
  status,
  error,
}: {
  score: StyleScore | null;
  status: "idle" | "loading" | "error" | "success";
  error: string | null;
}) {
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

  if (status === "idle") {
    return (
      <div style={{ color: "#aaa", textAlign: "center", padding: 20 }}>
        No outfit data available. Please analyze patterns first.
      </div>
    );
  }

  if (status === "loading") {
    return (
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
    );
  }

  if (status === "error") {
    return (
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
    );
  }

  if (!score) {
    return null;
  }

  return (
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
  );
}

export default ScoreSection;
