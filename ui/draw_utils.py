# draw_utils.py
from __future__ import annotations
import cv2
from typing import Iterable, Tuple, Sequence, Optional, Union

import mediapipe as mp
from mediapipe.python.solutions import pose as mp_pose

try:
    MP_POSE_ENUM = mp_pose.PoseLandmark
except Exception:
    MP_POSE_ENUM = None  # optional; only used for name->index helper


def _to_px(x: float, y: float, w: int, h: int) -> Tuple[int, int]:
    return int(round(x * w)), int(round(y * h))


def _idx(name_or_idx: Union[int, str]) -> int:
    if isinstance(name_or_idx, int):
        return name_or_idx
    if MP_POSE_ENUM is None:
        raise ValueError("String landmark names require mediapipe installed.")
    return MP_POSE_ENUM[name_or_idx].value  # e.g., "LEFT_SHOULDER" -> 11


def draw_landmarks(
    img,
    lm_list,
    which: Iterable[Union[int, str]],
    color: Tuple[int, int, int] = (0, 255, 0),
    radius: int = 4,
    thickness: int = 2,
    visibility_min: float = 0.5,
    draw_index: bool = False
):
    """Draw specific landmarks by index or pose name."""
    h, w = img.shape[:2]
    for i0 in which:
        i = _idx(i0)
        if i >= len(lm_list):
            continue
        lm = lm_list[i]
        if hasattr(lm, "visibility") and lm.visibility < visibility_min:
            continue
        x, y = _to_px(lm.x, lm.y, w, h)
        cv2.circle(img, (x, y), radius, color, -1, lineType=cv2.LINE_AA)
        if draw_index:
            cv2.putText(img, str(i), (x+6, y-6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


def draw_connections(
    img,
    lm_list,
    pairs: Iterable[Tuple[Union[int, str], Union[int, str]]],
    color: Tuple[int, int, int] = (255, 255, 255),
    thickness: int = 2,
    visibility_min: float = 0.5
):
    """Draw custom connections (i,j) where i/j are indices or names."""
    h, w = img.shape[:2]
    for a0, b0 in pairs:
        a = _idx(a0)
        b = _idx(b0)
        if a >= len(lm_list) or b >= len(lm_list):
            continue
        la, lb = lm_list[a], lm_list[b]
        if hasattr(la, "visibility") and la.visibility < visibility_min:
            continue
        if hasattr(lb, "visibility") and lb.visibility < visibility_min:
            continue
        xa, ya = _to_px(la.x, la.y, w, h)
        xb, yb = _to_px(lb.x, lb.y, w, h)
        cv2.line(img, (xa, ya), (xb, yb), color,
                 thickness, lineType=cv2.LINE_AA)


def draw_axes(img, lm, size: int = 40, thickness: int = 2):
    """Optional: draw local XYZ axes for a landmark (uses z for sign)."""
    h, w = img.shape[:2]
    x, y = _to_px(lm.x, lm.y, w, h)
    cv2.circle(img, (x, y), 3, (0, 0, 0), -1, cv2.LINE_AA)
    cv2.line(img, (x, y), (x+size, y), (0, 0, 255),
             thickness, cv2.LINE_AA)   # X red
    cv2.line(img, (x, y), (x, y-size), (0, 255, 0),
             thickness, cv2.LINE_AA)   # Y green
    # Z is not directly drawable in 2D; you can encode sign by color/thickness if desired.
