from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import cv2
import mediapipe as mp


@dataclass
class BgBlurConfig:
    mask_thresh: float = 0.1      # 0..1; lower → more foreground retained
    ksize: int = 31               # odd kernel size for GaussianBlur
    dilate: int = 2               # px radius to expand mask edges
    erode: int = 0                # px radius to contract mask edges
    model_selection: int = 1      # 0 close-range, 1 landscape


class BgBlur:
    def __init__(self, cfg: BgBlurConfig = BgBlurConfig()) -> None:
        self.cfg = cfg
        self._mp_selfie = mp.solutions.selfie_segmentation.SelfieSegmentation(  # type: ignore
            model_selection=cfg.model_selection
        )

    def _refine_mask(self, mask: np.ndarray) -> np.ndarray:
        """mask: HxW float32 0..1 → returns HxW uint8 0/255 with morph ops."""
        m = (mask > float(self.cfg.mask_thresh)).astype(np.uint8) * 255
        if self.cfg.dilate > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                          (self.cfg.dilate*2+1, self.cfg.dilate*2+1))
            m = cv2.dilate(m, k, iterations=1)
        if self.cfg.erode > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                          (self.cfg.erode*2+1, self.cfg.erode*2+1))
            m = cv2.erode(m, k, iterations=1)
        return m

    def apply(self, rgb: np.ndarray) -> np.ndarray:
        """Input/Output: RGB uint8 HxWx3. Returns blurred-bg composite (same size)."""
        # MediaPipe expects RGB
        res = self._mp_selfie.process(rgb)
        raw = res.segmentation_mask.astype(np.float32)  # HxW float
        m = self._refine_mask(raw)                      # HxW uint8 0/255

        # Background blur (same size); cv2 works fine in RGB
        k = self.cfg.ksize if self.cfg.ksize % 2 == 1 else self.cfg.ksize + 1
        blurred = cv2.GaussianBlur(rgb, (k, k), 0)

        # Composite: keep foreground sharp, background blurred
        fg = cv2.bitwise_and(rgb, rgb, mask=m)
        inv = cv2.bitwise_not(m)
        bg = cv2.bitwise_and(blurred, blurred, mask=inv)
        out = cv2.add(fg, bg)
        return out
