# server.py
import io
import base64
from PIL import Image
import numpy as np
from flask import Flask
from flask_socketio import SocketIO, emit

from detection.yolo_detector import YoloClothesDetector
from config import defaults

detector = YoloClothesDetector(weights_path=defaults.MODEL_PATH,
                               device=defaults.DEVICE, imgsz=defaults.IMGSZ, conf=defaults.CONF_THRESH)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


def segment_frame(arr_rgb: np.ndarray):
    # TODO: call your detector + convert masks to polygons/bboxes
    # return {"width": W, "height": H, "items":[{"id":"g0", "bbox":[x,y,w,h], "label":"shirt"}]}
    H, W = arr_rgb.shape[:2]
    dets = detector.predict(arr_rgb)

    items = [{"id": f"g{idx}", "bbox": [x1, y1, x2-x1, y2-y1], "label": detector.class_names[class_id]}
             for idx, (x1, y1, x2, y2, class_id, score) in enumerate(dets)]

    return {"width": W, "height": H, "items": items}


@socketio.on("frame")
def on_frame(msg):
    # msg = data URL "data:image/webp;base64,...."
    b64 = msg.split(",", 1)[1]
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    arr = np.array(img)
    seg = segment_frame(arr)
    emit("segmentation", seg)


@socketio.on("analyze_patterns")
def on_analyze(items):
    # items: [{id, label, cropDataUrl}]
    # HERE: call your LLM module (same one we drafted) and return patterns
    # For now, fake it:
    out = [{"id": it["id"], "label": it["label"],
            "pattern": "striped", "confidence": 0.82} for it in items]
    emit("patterns", out)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
