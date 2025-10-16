import { DefaultEventsMap } from "socket.io/dist/typed-events";

// Payloads from your backend
export interface SegmentationItem {
  id: string;
  bbox: [number, number, number, number];
  label: string;
  score?: number;
}

export interface SegmentationPayload {
  width: number;
  height: number;
  items: SegmentationItem[];
  error?: string;
}

export interface PatternResult {
  id: string;
  label: string;
  pattern: string;
  confidence?: number;
}

export interface PatternRequest {
  id: string;
  label: string;
  cropDataUrl: string;
}

// Socket.IO typing
export interface ServerToClientEvents extends DefaultEventsMap {
  segmentation: (data: SegmentationPayload) => void;
  patterns: (results: PatternResult[]) => void;
}

export interface ClientToServerEvents extends DefaultEventsMap {
  frame: (dataUrl: string) => void;
  analyze_patterns: (items: PatternRequest[]) => void;
}
