import React from "react";
import type { ConnStatus } from "../hooks/useSocket";

export default function ConnectionOverlay({ status }: { status: ConnStatus }) {
  if (status === "connected") return null;

  const text =
    status === "connecting" ? "Connecting…" : "Disconnected. Reconnecting…";

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "grid",
        placeItems: "center",
        borderRadius: 12,
        zIndex: 5,
      }}
    >
      <div
        style={{
          display: "grid",
          gap: 12,
          placeItems: "center",
          padding: 16,
          backdropFilter: "blur(2px)",
        }}
      >
        <div
          aria-label="loading"
          style={{
            width: 48,
            height: 48,
            border: "4px solid rgba(255,255,255,0.35)",
            borderTopColor: "white",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
          }}
        />
        <div style={{ color: "#fff", fontSize: 14 }}>{text}</div>
      </div>

      {/* keyframes (scoped) */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
