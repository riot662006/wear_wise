// src/App.tsx
import { useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client";

type Item = {
  id: string;
  bbox: [number, number, number, number];
  label?: string;
};

export default function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const socketRef = useRef<Socket | null>(null);
  const inflight = useRef(false);

  const [seg, setSeg] = useState<{
    width: number;
    height: number;
    items: Item[];
  } | null>(null);
  const [renderSize, setRenderSize] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const socket = io("http://localhost:5000");
    socketRef.current = socket;

    socket.on("segmentation", (data) => {
      setSeg(data);
      inflight.current = false; // allow next frame
    });
    socket.on("patterns", (res) => {
      // attach patterns to items for display
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
    });

    return () => {
      socket.disconnect();
    };
  }, []);

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

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d", { willReadFrequently: true })!;

    let raf = 0;
    const tick = () => {
      const socket = socketRef.current;
      if (!socket || socket.disconnected) {
        raf = requestAnimationFrame(tick);
        return;
      }

      const vw = video.videoWidth,
        vh = video.videoHeight;
      if (vw && vh && !inflight.current) {
        const targetW = 640;
        const scale = targetW / vw;
        const targetH = Math.round(vh * scale);
        canvas.width = targetW;
        canvas.height = targetH;
        ctx.drawImage(video, 0, 0, targetW, targetH);
        const dataUrl = canvas.toDataURL("image/webp", 0.75);
        inflight.current = true;
        socket.emit("frame", dataUrl);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

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
    const socket = socketRef.current;
    const video = videoRef.current;
    const s = seg;
    if (!socket || !video || !s) return;

    // make tiny crops for each item and send as data URLs
    const crops = await Promise.all(
      s.items.map(async (it) => {
        // crop from CURRENT FRAME to keep simple
        // const vw = video.videoWidth,
        //   vh = video.videoHeight;
        const c = document.createElement("canvas");
        const cx = c.getContext("2d")!;
        const [x, y, w, h] = it.bbox;
        c.width = w;
        c.height = h;
        cx.drawImage(video, x, y, w, h, 0, 0, w, h);
        return {
          id: it.id,
          label: it.label ?? "garment",
          cropDataUrl: c.toDataURL("image/jpeg", 0.9),
        };
      })
    );
    socket.emit("analyze_patterns", crops);
  };

  const sx = seg && renderSize.w ? renderSize.w / seg.width : 1;
  const sy = seg && renderSize.h ? renderSize.h / seg.height : 1;

  return (
    <div
      style={{
        display: "grid",
        placeItems: "center",
        height: "100dvh",
        background: "#0a0a0a",
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
                    stroke="green"
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
                      fill="green"
                    >
                      {it.label}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        )}
        <div
          style={{
            position: "absolute",
            left: 12,
            top: 12,
            display: "flex",
            gap: 8,
          }}
        >
          <button
            onClick={requestPatterns}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              border: "1px solid #444",
              background: "#111",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            Analyze Patterns
          </button>
        </div>
      </div>
    </div>
  );
}
