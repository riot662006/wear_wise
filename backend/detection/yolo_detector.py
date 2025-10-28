from ultralytics import YOLO
import numpy as np
import torch
from typing import List, Tuple, Optional

class YoloClothesDetector:
    """
    Wraps Ultralytics YOLO for clothes detection.

    Returns list of detections: [(x1, y1, x2, y2, class_id, score)]
    """
    def __init__(self, weights_path, device="cpu", imgsz=640, conf=0.25, classes: Optional[list[int]] = None):
        self.model = YOLO(str(weights_path))
        self.device = device
        self.imgsz = imgsz
        self.conf = conf
        self.classes = classes
        if torch.cuda.is_available() and device == "cuda":
            self.model.to("cuda")

        # names dict: {id: "class_name", ...}
        self.class_names = self.model.model.names

    def predict(self, bgr_image: np.ndarray) -> List[Tuple[int, int, int, int, int, float]]:
        res = self.model.predict(
            bgr_image,
            imgsz=self.imgsz,
            conf=self.conf,
            verbose=False,
            device=self.device,
            classes=self.classes
        )[0]

        out = []
        if not hasattr(res, "boxes") or res.boxes is None or len(res.boxes) == 0:
            return out

        xyxy = res.boxes.xyxy.detach().cpu().numpy().astype(int)
        cls  = res.boxes.cls.detach().cpu().numpy().astype(int)
        conf = res.boxes.conf.detach().cpu().numpy()

        for (x1, y1, x2, y2), c, s in zip(xyxy, cls, conf):
            out.append((int(x1), int(y1), int(x2), int(y2), int(c), float(s)))
        return out
