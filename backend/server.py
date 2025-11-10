# server.py
import io
import base64
from typing import Any, Dict, List
from PIL import Image
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from services.ai_schemas import PatternRequest
from preprocess.bg_blur import BgBlur, BgBlurConfig
from preprocess.utils import clamp_xywh, parse_det, xyxy_to_xywh
from services.ai_client import AIClient
from detection.yolo_detector import YoloClothesDetector
from config import defaults
from scoring import score_outfit, OutfitFeatures, load_config

bg_blur = BgBlur(BgBlurConfig(mask_thresh=0.10, ksize=31,
                 dilate=2, erode=0, model_selection=1))

detector = YoloClothesDetector(weights_path=defaults.MODEL_PATH,
                               device=defaults.DEVICE, imgsz=defaults.IMGSZ, conf=defaults.CONF_THRESH)

ai_client = AIClient()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173"]}}, supports_credentials=True)

socketio = SocketIO(app, cors_allowed_origins="*")


def segment_frame(arr_rgb: np.ndarray, srcW: int, srcH: int) -> dict:
    Hd, Wd = arr_rgb.shape[:2]

    arr_rgb_for_det = bg_blur.apply(arr_rgb)
    dets = detector.predict(arr_rgb_for_det)

    sx = srcW / Wd
    sy = srcH / Hd

    items: List[Dict] = []
    for i, d in enumerate(dets):
        x1, y1, x2, y2, conf, cls_idx = parse_det(d)

        # det space → video space
        X1 = x1 * sx
        Y1 = y1 * sy
        X2 = x2 * sx
        Y2 = y2 * sy

        x, y, w, h = xyxy_to_xywh(X1, Y1, X2, Y2)
        x, y, w, h = clamp_xywh(x, y, w, h, srcW, srcH)

        if w < 8 or h < 8:
            continue

        label = detector.class_names[cls_idx] if 0 <= cls_idx < len(
            detector.class_names) else "garment"
        items.append({
            "id": f"g{i}",
            "bbox": [x, y, w, h],   # already in VIDEO coords
            "label": label,
            "score": round(float(conf), 3),
        })

    # return the **video-native** size
    return {"width": srcW, "height": srcH, "items": items}


@socketio.on("frame")
def on_frame(payload: Dict[str, Any]):
    # payload: { "dataUrl": "data:image/webp;base64,...", "srcW": int, "srcH": int }
    try:
        data_url = payload["dataUrl"]
        srcW = int(payload["srcW"])
        srcH = int(payload["srcH"])

        b64 = data_url.split(",", 1)[1]
        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        arr = np.array(img)  # det-sized array

        seg = segment_frame(arr, srcW=srcW, srcH=srcH)
        emit("segmentation", seg)
    except Exception as e:
        emit("segmentation", {"width": 0, "height": 0,
             "items": [], "error": str(e)})


@socketio.on("analyze_patterns")
def on_analyze(items: list[PatternRequest]):
    """
    items: [{ id, label, cropDataUrl }]
    Returns: emit("patterns", [{ id, label, pattern, confidence, notes? }])
    """
    try:
        # basic sanity filter: ignore missing/empty data URLs
        clean: list[PatternRequest] = [
            it for it in items
            if isinstance(it.get("id"), str)
            and isinstance(it.get("label"), str)
            and isinstance(it.get("cropDataUrl"), str)
            and it["cropDataUrl"].startswith("data:image/")
        ]
        results = ai_client.analyze_batch(clean, max_concurrency=3)
        print(results)
        emit("patterns", results)
    except Exception as e:
        # Fall back with per-item errors so the modal can show failures
        fallback = [{
            "id": it.get("id", f"unk_{i}"),
            "label": it.get("label", "garment"),
            "pattern": "other",
            "confidence": 0.0,
            "error": f"ServerError: {e}",
        } for i, it in enumerate(items)]
        emit("patterns", fallback)


@app.route("/api/style/score", methods=["POST"])
def api_style_score():
    """
    POST /api/style/score
    
    Body: OutfitFeatures (JSON)
    Returns: StyleScore (JSON)
    
    Idempotent: Same input → same output.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        
        # Validate required fields
        required_fields = ["outfitId", "garments", "colorClusters", "thirdsArea", "domainZ", "extractionVersion"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({"error": f"Missing required fields: {missing}"}), 400
        
        # Convert to OutfitFeatures (type checking is lenient for API)
        features: OutfitFeatures = {
            "outfitId": str(data["outfitId"]),
            "garments": data["garments"],
            "colorClusters": data["colorClusters"],
            "thirdsArea": data["thirdsArea"],
            "domainZ": data["domainZ"],
            "body": data.get("body"),
            "extractionVersion": str(data["extractionVersion"]),
        }
        
        # Score the outfit
        result = score_outfit(features)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"error": f"Scoring failed: {str(e)}"}), 500


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
