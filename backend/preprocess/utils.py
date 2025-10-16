
from typing import Any, Tuple


def xyxy_to_xywh(x1: float, y1: float, x2: float, y2: float) -> Tuple[int, int, int, int]:
    return int(x1), int(y1), int(x2 - x1), int(y2 - y1)


def clamp_xywh(x: int, y: int, w: int, h: int, W: int, H: int) -> Tuple[int, int, int, int]:
    if x < 0:
        x = 0
    if y < 0:
        y = 0
    if x > W - 1:
        x = W - 1
    if y > H - 1:
        y = H - 1
    if x + w > W:
        w = W - x
    if y + h > H:
        h = H - y
    if w < 1:
        w = 1
    if h < 1:
        h = 1
    return x, y, w, h


def parse_det(det: Any) -> Tuple[float, float, float, float, float, int]:
    # supports tuple or dict
    if isinstance(det, dict):
        x1 = float(det.get("x1", det.get("xmin", 0)))
        y1 = float(det.get("y1", det.get("ymin", 0)))
        x2 = float(det.get("x2", det.get("xmax", 0)))
        y2 = float(det.get("y2", det.get("ymax", 0)))
        conf = float(det.get("conf", det.get("confidence", 0)))
        cls_idx = int(det.get("cls", det.get("class", 0)))
        return x1, y1, x2, y2, conf, cls_idx
    x1, y1, x2, y2, conf, cls_idx = det[:6]
    return float(x1), float(y1), float(x2), float(y2), float(conf), int(cls_idx)
