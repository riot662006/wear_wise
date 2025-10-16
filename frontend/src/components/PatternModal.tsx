import React from "react";
import Modal from "./Modal";

export type PatternItem = {
  id: string;
  label: string;
  cropDataUrl: string;
  pattern?: string | null;
  confidence?: number | null;
  error?: string | null;
};

export default function PatternModal({
  open,
  items,
  onClose,
}: {
  open: boolean;
  items: PatternItem[];
  onClose: () => void;
}) {
  return (
    <Modal open={open} title="Pattern Analysis" onClose={onClose}>
      {items.length === 0 ? (
        <div style={{ color: "#aaa" }}>No items to analyze.</div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: 16,
          }}
        >
          {items.map((it) => (
            <div
              key={it.id}
              style={{
                border: "1px solid #2a2a2a",
                borderRadius: 10,
                overflow: "hidden",
                background: "#0f0f0f",
              }}
            >
              <div
                style={{
                  aspectRatio: "1 / 1",
                  background: "#111",
                  position: "relative",
                }}
              >
                <img
                  src={it.cropDataUrl}
                  alt={it.label}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    display: "block",
                  }}
                />
                {/* per-card spinner/status */}
                {it.pattern === undefined && !it.error && (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      display: "grid",
                      placeItems: "center",
                      background: "rgba(0,0,0,0.35)",
                    }}
                  >
                    <div
                      aria-label="loading"
                      style={{
                        width: 28,
                        height: 28,
                        border: "3px solid rgba(255,255,255,0.35)",
                        borderTopColor: "white",
                        borderRadius: "50%",
                        animation: "spin 1s linear infinite",
                      }}
                    />
                  </div>
                )}
                <style>{`
                  @keyframes spin { to { transform: rotate(360deg); } }
                `}</style>
              </div>

              <div style={{ padding: 10 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {it.label}
                </div>

                {it.error ? (
                  <div style={{ color: "#ff6b6b", fontSize: 14 }}>
                    Error: {it.error}
                  </div>
                ) : it.pattern === undefined ? (
                  <div style={{ color: "#aaa", fontSize: 14 }}>Analyzing…</div>
                ) : (
                  <div style={{ fontSize: 14 }}>
                    <span style={{ color: "#8ef" }}>Pattern:</span>{" "}
                    {it.pattern ?? "other"}
                    {typeof it.confidence === "number" && (
                      <span style={{ color: "#aaa" }}>
                        {" "}
                        ({(it.confidence * 100).toFixed(0)}%)
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
