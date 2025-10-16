// src/App.tsx
import { useEffect, useRef, useState } from "react";
import { Socket } from "socket.io-client";
import { useSocket } from "./hooks/useSocket";
import ConnectionOverlay from "./components/ConnectionOverlay";

type Item = {
  id: string;
  bbox: [number, number, number, number];
  label?: string;
};

export default function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const inflight = useRef(false);
  const { socket: socketRef, status } = useSocket({ url: "http://localhost:5000" });

  const [seg, setSeg] = useState<{
    width: number;
    height: number;
    items: Item[];
  } | null>(null);
  const [renderSize, setRenderSize] = useState({ w: 0, h: 0 });

  // Socket event wiring
  useEffect(() => {
    const socket = socketRef.current as Socket | null;
    if (!socket) return;

    const onSeg = (data: any) => {
      setSeg(data);
      inflight.current = false;
    };
    const onPatterns = (res: any[]) => {
      setSeg((s) =>
        s
          ? {
              ...s,
              items: s.items.map((it) => {
                const match = res.find((r: any) => r.id === it.id);
                return match
                  ? { ...it, label: `${it.label ?? "item"} • ${match.pattern}` }
                  : it;
              }),
            }
          : s
      );
    };

    socket.on("segmentation", onSeg);
    socket.on("patterns", onPatterns);

    return () => {
      socket.off("segmentation", onSeg);
      socket.off("patterns", onPatterns);
    };
  }, [socketRef]);

  // Camera setup
  useEffect(() => {
    (async () => {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => videoRef.current?.play();
      }
    })();
  }, []);

  // Pause / resume video based on connection status
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;

    if (status === "connected") {
      // resume
      v.play().catch(() => {});
    } else {
      // pause feed display while we reconnect
      v.pause();
    }
  }, [status]);

  // Frame loop (only when connected)
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d", { willReadFrequently: true })!;

    let raf = 0;
    const tick = () => {
      const socket = socketRef.current;
      const connected = status === "connected";

      if (!socket || !connected) {
        raf = requestAnimationFrame(tick);
        return;
      }

      const vw = v.videoWidth,
        vh = v.videoHeight;
      if (vw && vh && !inflight.current) {
        const targetW = 640;
        const scale = targetW / vw;
        const targetH = Math.round(vh * scale);
        canvas.width = targetW;
        canvas.height = targetH;
        ctx.drawImage(v, 0, 0, targetW, targetH);
        const dataUrl = canvas.toDataURL("image/webp", 0.75);
        inflight.current = true;
        (socket as any).emit("frame", dataUrl);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [socketRef, status]);

  // measure render box
  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() =>
      setRenderSize({ w: el.clientWidth, h: el.clientHeight })
    );
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const requestPatterns = async () => {
    const socket = socketRef.current as Socket | null;
    const v = videoRef.current;
    const s = seg;
    if (!socket || !v || !s || status !== "connected") return;

    const crops = await Promise.all(
      s.items.map(async (it) => {
        const c = document.createElement("canvas");
        const cx = c.getContext("2d")!;
        const [x, y, w, h] = it.bbox;
        c.width = w;
        c.height = h;
        cx.drawImage(v, x, y, w, h, 0, 0, w, h);
        return {
          id: it.id,
          label: it.label ?? "garment",
          cropDataUrl: c.toDataURL("image/jpeg", 0.9),
        };
      })
    );
    (socket as any).emit("analyze_patterns", crops);
  };

  const sx = seg && renderSize.w ? renderSize.w / seg.width : 1;
  const sy = seg && renderSize.h ? renderSize.h / seg.height : 1;

  return (
    <div
      style={{
        display: "grid",
        placeItems: "center",
        height: "100dvh",
        background: "#494949",
        color: "#fff",
      }}
    >
      <div style={{ position: "relative", width: "min(90vw, 960px)" }}>
        <video
          ref={videoRef}
          style={{ width: "100%", borderRadius: 12, display: "block" }}
          muted
          playsInline
        />
        {/* bbox overlay */}
        {seg && (
          <svg
            style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
            viewBox={`0 0 ${renderSize.w} ${renderSize.h}`}
            preserveAspectRatio="none"
          >
            {seg.items.map((it) => {
              const [x, y, w, h] = it.bbox;
              return (
                <g key={it.id}>
                  <rect
                    x={x * sx}
                    y={y * sy}
                    width={w * sx}
                    height={h * sy}
                    fill="none"
                    stroke="white"
                    strokeOpacity={0.95}
                    strokeWidth={2}
                    rx={6}
                    ry={6}
                  />
                  {it.label && (
                    <text
                      x={x * sx + 8}
                      y={y * sy + 20}
                      fontSize="14"
                      fill="white"
                    >
                      {it.label}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        )}

        {/* spinner + pause overlay when not connected */}
        <ConnectionOverlay status={status} />

        {/* Controls */}
        <div
          style={{
            position: "absolute",
            left: 12,
            top: 12,
            display: "flex",
            gap: 8,
            zIndex: 10,
          }}
        >
          <button
            onClick={requestPatterns}
            disabled={status !== "connected"}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              border: "1px solid #444",
              background: status === "connected" ? "#111" : "#333",
              color: "#fff",
              cursor: status === "connected" ? "pointer" : "not-allowed",
            }}
          >
            Analyze Patterns
          </button>
        </div>
      </div>
    </div>
  );
}
