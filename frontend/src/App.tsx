import { useEffect, useRef, useState } from "react";
import { Socket } from "socket.io-client";
import { useSocket } from "./hooks/useSocket";

import ConnectionOverlay from "./components/ConnectionOverlay";
import PatternModal, { type PatternItem } from "./components/PatternModal";
import { scaleClampXYWH } from "./utils/geometry";
import { BoundingBoxOverlay } from "./components/BoundingBoxOverlay";

type Item = {
  id: string;
  bbox: [number, number, number, number];
  label?: string;
};

export default function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const inflight = useRef(false);
  const { socket: socketRef, status } = useSocket({
    url: "http://localhost:5000",
  });

  const [seg, setSeg] = useState<{
    width: number;
    height: number;
    items: Item[];
  } | null>(null);
  const [renderSize, setRenderSize] = useState({ w: 0, h: 0 });

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalItems, setModalItems] = useState<PatternItem[]>([]);

  const sx = seg && renderSize.w ? renderSize.w / seg.width : 1;
  const sy = seg && renderSize.h ? renderSize.h / seg.height : 1;

  // Socket event wiring
  useEffect(() => {
    const socket = socketRef.current as Socket | null;
    if (!socket) return;

    const onSeg = (data: any) => {
      setSeg(data);
      inflight.current = false;
    };
    const onPatterns = (res: any[]) => {
      // merge results into modal items by id
      setModalItems((prev) =>
        prev.map((it) => {
          const m = res.find((r: any) => r.id === it.id);
          return m
            ? {
                ...it,
                pattern: m.pattern ?? "other",
                confidence:
                  typeof m.confidence === "number" ? m.confidence : null,
                error: null,
              }
            : it;
        })
      );
      // also annotate live labels if you want
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

  // Pause/resume video based on connection AND modal state
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const shouldPlay = status === "connected" && !isModalOpen;
    if (shouldPlay) v.play().catch(() => {});
    else v.pause();
  }, [status, isModalOpen]);

  // Frame loop (only when connected AND modal is closed)
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d", { willReadFrequently: true })!;

    let raf = 0;
    const tick = () => {
      const socket = socketRef.current;
      const connected = status === "connected";
      if (!socket || !connected || isModalOpen) {
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
  }, [socketRef, status, isModalOpen]);

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

  // Opens modal, pauses video/emission (handled by isModalOpen), kicks off analysis
  const openAnalysisModal = async () => {
    const socket = socketRef.current as Socket | null;
    const v = videoRef.current;
    const s = seg;
    if (!socket || !v || !s || status !== "connected") return;

    // scale from segmentation coords → video coords
    const vw = v.videoWidth,
      vh = v.videoHeight;
    const sxVid = vw / s.width;
    const syVid = vh / s.height;

    const crops: PatternItem[] = await Promise.all(
      s.items.map(async (it) => {
        const [x0, y0, w0, h0] = it.bbox; // bbox in seg space
        const [x, y, w, h] = scaleClampXYWH(
          [x0, y0, w0, h0],
          sxVid,
          syVid,
          vw,
          vh
        );

        const c = document.createElement("canvas");
        const cx = c.getContext("2d")!;
        c.width = w;
        c.height = h;
        // crop from the CURRENT video frame in video pixel space
        cx.drawImage(v, x, y, w, h, 0, 0, w, h);

        return {
          id: it.id,
          label: it.label ?? "garment",
          cropDataUrl: c.toDataURL("image/jpeg", 0.9),
          pattern: undefined, // spinner until results arrive
          confidence: null,
          error: null,
        };
      })
    );

    setModalItems(crops);
    setIsModalOpen(true);
    (socket as any).emit(
      "analyze_patterns",
      crops.map(({ id, label, cropDataUrl }) => ({ id, label, cropDataUrl }))
    );
  };

  const closeModal = () => {
    setIsModalOpen(false); // video + emission resumes via effects
  };

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

        {/* bbox overlay */}
        {seg && (
          <BoundingBoxOverlay
            items={seg.items}
            naturalW={seg.width}
            naturalH={seg.height}
            renderW={renderSize.w}
            renderH={renderSize.h}
            stroke="white"
            strokeWidth={2}
            showLabels
          />
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
            onClick={openAnalysisModal}
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
            Analyze Patterns (Modal)
          </button>
        </div>
      </div>

      {/* Pattern results modal (pauses video & emission while open) */}
      <PatternModal
        open={isModalOpen}
        items={modalItems}
        onClose={closeModal}
      />
    </div>
  );
}
