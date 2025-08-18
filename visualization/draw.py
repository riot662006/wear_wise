import cv2
import numpy as np
from typing import List, Tuple, Dict

def draw_detections(bgr_frame: np.ndarray,
                    rects: List[Tuple[int, int, int, int, int, float]],
                    class_names: Dict[int, str],
                    color=(0, 255, 255),
                    thickness=2) -> np.ndarray:
    out = bgr_frame.copy()
    for (x1, y1, x2, y2, c, s) in rects:
        label = f"{class_names.get(c, str(c))} {s:.2f}"
        cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness)
        (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        y_text = max(y1 - 8, th + 4)
        cv2.rectangle(out, (x1, y_text - th - 6), (x1 + tw + 6, y_text + 2), color, -1)
        cv2.putText(out, label, (x1 + 3, y_text - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
    return out

def draw_hud(bgr_frame: np.ndarray, text: str) -> np.ndarray:
    out = bgr_frame.copy()
    cv2.putText(out, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(out, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
    return out
