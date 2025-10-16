# server.py
import io
import base64
from PIL import Image
import numpy as np
from flask import Flask
from flask_socketio import SocketIO, emit

# TODO: import your YOLO clothes segmenter here
# from detection.yolo_detector import YoloClothesDetector
# detector = YoloClothesDetector(weights_path=..., device=..., imgsz=..., conf=...)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


def segment_frame(arr_rgb: np.ndarray):
    # TODO: call your detector + convert masks to polygons/bboxes
    # return {"width": W, "height": H, "items":[{"id":"g0", "bbox":[x,y,w,h], "label":"shirt"}]}
    H, W = arr_rgb.shape[:2]
    # fake
    return {"width": W, "height": H, "items": [{"id": "g0", "bbox": [200, 100, 120, 50], "label": "shirt"}]}


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
