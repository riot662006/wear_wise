import React, { memo } from "react";

export type BBox = [number, number, number, number];
export type OverlayItem = {
  id: string;
  bbox: BBox; // [x, y, w, h] in NATURAL coords (seg.width/height)
  label?: string;
};

type Props = {
  items: OverlayItem[];
  naturalW: number; // e.g., seg.width
  naturalH: number; // e.g., seg.height
  renderW: number; // measured video element width
  renderH: number; // measured video element height
  stroke?: string; // hex or css color
  strokeWidth?: number;
  showLabels?: boolean;
  className?: string; // optional extra classes
  style?: React.CSSProperties;
};

function _Overlay({
  items,
  naturalW,
  naturalH,
  renderW,
  renderH,
  stroke = "white",
  strokeWidth = 2,
  showLabels = true,
  className,
  style,
}: Props) {
  if (!items?.length || !naturalW || !naturalH || !renderW || !renderH)
    return null;

  const sx = renderW / naturalW;
  const sy = renderH / naturalH;

  return (
    <svg
      className={className}
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        ...style,
      }}
      viewBox={`0 0 ${renderW} ${renderH}`}
      preserveAspectRatio="none"
    >
      {items.map((it) => {
        const [x, y, w, h] = it.bbox;
        const rx = x * sx,
          ry = y * sy,
          rw = w * sx,
          rh = h * sy;
        return (
          <g key={it.id}>
            <rect
              x={rx}
              y={ry}
              width={rw}
              height={rh}
              fill="none"
              stroke={stroke}
              strokeOpacity={0.95}
              strokeWidth={strokeWidth}
              rx={6}
              ry={6}
            />
            {showLabels && it.label && (
              <text
                x={rx + 8}
                y={ry + 20}
                fontSize="14"
                fill={stroke}
                style={{
                  paintOrder: "stroke",
                  stroke: "rgba(0,0,0,0.6)",
                  strokeWidth: 2,
                }}
              >
                {it.label}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

// memo to avoid unnecessary re-renders when props are unchanged
export const BoundingBoxOverlay = memo(_Overlay);
