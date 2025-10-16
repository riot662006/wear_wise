import React, { useEffect } from "react";

type ModalProps = {
  open: boolean;
  title?: string;
  onClose: () => void;
  children: React.ReactNode;
};

export default function Modal({ open, title, onClose, children }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "grid",
        placeItems: "center",
        background: "rgba(0,0,0,0.6)",
        padding: 16,
      }}
      onClick={(e) => {
        // click backdrop to close
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: "min(95vw, 900px)",
          maxHeight: "85vh",
          background: "#121212",
          color: "#fff",
          borderRadius: 12,
          border: "1px solid #2a2a2a",
          boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
          display: "grid",
          gridTemplateRows: "auto 1fr auto",
        }}
      >
        <div
          style={{
            padding: "14px 16px",
            borderBottom: "1px solid #2a2a2a",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 600 }}>
            {title ?? "Details"}
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              border: "1px solid #3a3a3a",
              background: "#1a1a1a",
              color: "#fff",
              borderRadius: 8,
              padding: "6px 10px",
              cursor: "pointer",
            }}
          >
            ✕
          </button>
        </div>

        <div
          style={{
            overflowY: "auto",
            padding: 16,
          }}
        >
          {children}
        </div>

        <div
          style={{
            padding: 12,
            borderTop: "1px solid #2a2a2a",
            display: "flex",
            justifyContent: "flex-end",
            gap: 8,
          }}
        >
          <button
            onClick={onClose}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              border: "1px solid #444",
              background: "#1b1b1b",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
