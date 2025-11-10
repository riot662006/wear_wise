import { useEffect, useRef, useState } from "react";
import { useSocket } from "./hooks/useSocket";

import ConnectionOverlay from "./components/ConnectionOverlay";
import PatternModal, { type PatternItem } from "./components/PatternModal";
import StyleScoreModal from "./components/StyleScoreModal";
import { BoundingBoxOverlay } from "./components/BoundingBoxOverlay";
import type { PatternResult, SegmentationPayload } from "./types/socket";
import { createOutfitFeatures } from "./utils/outfitFeatures";
import type { OutfitFeatures } from "./types/styleScore";

export default function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const inflight = useRef(false);
  const { socket: socketRef, status } = useSocket({
    url: "http://localhost:5000",
  });

  const [seg, setSeg] = useState<SegmentationPayload | null>(null);
  const [renderSize, setRenderSize] = useState({ w: 0, h: 0 });

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalItems, setModalItems] = useState<PatternItem[]>([]);
  const [isScoreModalOpen, setIsScoreModalOpen] = useState(false);
  const [outfitFeatures, setOutfitFeatures] = useState<OutfitFeatures | null>(null);
  const [patternResults, setPatternResults] = useState<PatternResult[]>([]);

  // Socket event wiring
  useEffect(() => {
    const socket = socketRef.current;
    if (!socket) return;

    const onSeg = (data: SegmentationPayload) => {
      setSeg(data);
      inflight.current = false;
    };
    const onPatterns = (res: PatternResult[]) => {
      // Store pattern results for style scoring
      setPatternResults(res);
      
      // merge results into modal items by id
      setModalItems((prev) =>
        prev.map((it) => {
          const m = res.find((r: PatternResult) => r.id === it.id);
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
                const match = res.find((r: PatternResult) => r.id === it.id);
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
    const shouldPlay = status === "connected" && !isModalOpen && !isScoreModalOpen;
    if (shouldPlay) v.play().catch(() => {});
    else v.pause();
  }, [status, isModalOpen, isScoreModalOpen]);

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
        socket.emit("frame", { dataUrl, srcW: vw, srcH: vh }); // 👈 send native size
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [socketRef, status, isModalOpen, isScoreModalOpen]);

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
    const socket = socketRef.current;
    const v = videoRef.current;
    const s = seg;
    if (!socket || !v || !s || status !== "connected") return;

    const crops: PatternItem[] = await Promise.all(
      s.items.map(async (it) => {
        const [x, y, w, h] = it.bbox; // video-native coords
        const c = document.createElement("canvas");
        const cx = c.getContext("2d")!;
        c.width = w;
        c.height = h;
        cx.drawImage(v, x, y, w, h, 0, 0, w, h);
        return {
          id: it.id,
          label: it.label ?? "garment",
          cropDataUrl: c.toDataURL("image/jpeg", 0.9),
          pattern: undefined,
          confidence: null,
          error: null,
        };
      })
    );

    setModalItems(crops);
    setIsModalOpen(true);
    socket.emit(
      "analyze_patterns",
      crops.map(({ id, label, cropDataUrl }) => ({ id, label, cropDataUrl }))
    );
  };

  const closeModal = () => {
    setIsModalOpen(false); // video + emission resumes via effects
  };

  const openScoreModal = () => {
    if (!seg || patternResults.length === 0) {
      alert("Please analyze patterns first before scoring style.");
      return;
    }
    
    // Create outfit features from current segmentation and patterns
    const features = createOutfitFeatures(seg, patternResults);
    setOutfitFeatures(features);
    setIsScoreModalOpen(true);
  };

  const closeScoreModal = () => {
    setIsScoreModalOpen(false);
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
            stroke="green"
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
            flexWrap: "wrap",
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
            Analyze Patterns
          </button>
          <button
            onClick={openScoreModal}
            disabled={status !== "connected" || !seg || patternResults.length === 0}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              border: "1px solid #444",
              background:
                status === "connected" && seg && patternResults.length > 0
                  ? "#1a4d2e"
                  : "#333",
              color: "#fff",
              cursor:
                status === "connected" && seg && patternResults.length > 0
                  ? "pointer"
                  : "not-allowed",
            }}
          >
            Score Style
          </button>
        </div>
      </div>

      {/* Pattern results modal (pauses video & emission while open) */}
      <PatternModal
        open={isModalOpen}
        items={modalItems}
        onClose={closeModal}
      />

      {/* Style score modal */}
      <StyleScoreModal
        open={isScoreModalOpen}
        onClose={closeScoreModal}
        features={outfitFeatures}
      />
    </div>
  );
}
