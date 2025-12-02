# server.py
import io
import base64
import time
from typing import Any, Dict, List
from PIL import Image
import numpy as np
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from services.ai_schemas import PatternRequest
from preprocess.bg_blur import BgBlur, BgBlurConfig
from preprocess.utils import clamp_xywh, compute_iou, parse_det, xyxy_to_xywh
from services.ai_client import AIClient
from detection.yolo_detector import YoloClothesDetector
from config import defaults
from scoring import score_outfit, OutfitFeatures, load_config
from scoring.features import create_outfit_features

bg_blur = BgBlur(BgBlurConfig(mask_thresh=0.10, ksize=31,
                 dilate=2, erode=0, model_selection=1))

detector = YoloClothesDetector(weights_path=defaults.MODEL_PATH,
                               device=defaults.DEVICE, imgsz=defaults.IMGSZ, conf=defaults.CONF_THRESH)

ai_client = AIClient()

app = Flask(__name__)
CORS(app, resources={
     r"/api/*": {"origins": ["http://localhost:5173"]}}, supports_credentials=True)

socketio = SocketIO(app, cors_allowed_origins="*")


# In-memory profiling buffer (simple, non-persistent). Use GET /api/profiling to inspect.
profiling_buffer: list[dict] = []
PROFILING_MAX = 200


def record_profile(entry: dict) -> None:
    """Append a profiling entry (bounded buffer)."""
    try:
        entry["ts"] = time.time()
        profiling_buffer.append(entry)
        # trim
        if len(profiling_buffer) > PROFILING_MAX:
            del profiling_buffer[0: len(profiling_buffer) - PROFILING_MAX]
    except Exception:
        pass


@app.route("/api/extract/features", methods=["POST"])
def api_extract_features():
    """
    POST /api/extract/features

    Body: { segmentation: {...}, patterns: [...], outfitId?: str, profile?: bool }
    Returns: OutfitFeatures (JSON)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        seg = data.get("segmentation")
        patterns = data.get("patterns", [])
        outfit_id = data.get("outfitId")
        want_profile = bool(data.get("profile", False)
                            or request.args.get("profile") == "1")

        if not seg or not isinstance(patterns, list):
            return jsonify({"error": "Missing segmentation or patterns"}), 400

        t0 = time.perf_counter()
        features = create_outfit_features(seg, patterns, outfit_id)
        extraction_ms = (time.perf_counter() - t0) * 1000.0

        # record profiling
        record_profile({"type": "extract_features", "extraction_ms": round(
            extraction_ms, 2), "items": len(patterns)})

        resp = {"features": features}
        if want_profile:
            resp["profiling"] = {"extraction_ms": round(extraction_ms, 2)}

        return jsonify(resp), 200
    except Exception as e:
        return jsonify({"error": f"Feature extraction failed: {e}"}), 500


@app.route("/api/profiling", methods=["GET", "POST"])
def api_profiling():
    """GET returns recent profiling entries. POST with {"clear": true} clears the buffer."""
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        if body.get("clear"):
            profiling_buffer.clear()
            return jsonify({"cleared": True}), 200
        return jsonify({"error": "Unsupported POST body"}), 400

    # GET
    return jsonify({"count": len(profiling_buffer), "entries": profiling_buffer}), 200


@app.route("/api/process_image", methods=["POST"])
def api_process_image():
    """
    End-to-end processing: detect -> analyze patterns -> extract features -> score

    Body (JSON): { dataUrl: string (data:image/...), srcW: int, srcH: int, outfitId?: str, profile?: bool }
    Returns: {
      segmentation, patterns, features, score, profiling: { detect_ms, analyze_ms, extraction_ms, scoring_ms }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        data_url = data.get("dataUrl")
        srcW = int(data.get("srcW", 0))
        srcH = int(data.get("srcH", 0))
        outfit_id = data.get("outfitId")
        want_profile = bool(data.get("profile", False)
                            or request.args.get("profile") == "1")

        if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
            return jsonify({"error": "Missing or invalid dataUrl"}), 400

        # decode image
        b64 = data_url.split(",", 1)[1]
        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        arr = np.array(img)

        # run detection/segmentation
        t0 = time.perf_counter()
        seg = segment_frame(arr, srcW=srcW or img.width,
                            srcH=srcH or img.height)
        detect_ms = (time.perf_counter() - t0) * 1000.0

        # build crops for analysis
        crops: List[Dict[str, Any]] = []
        for it in seg.get("items", []):
            bid = it.get("id")
            label = it.get("label", "garment")
            x, y, w, h = it.get("bbox", [0, 0, 0, 0])
            # ensure integer bounds and clip
            left = int(max(0, round(x)))
            upper = int(max(0, round(y)))
            right = int(min(img.width, round(x + w)))
            lower = int(min(img.height, round(y + h)))
            if right <= left or lower <= upper:
                continue

            crop = img.crop((left, upper, right, lower))
            buf = io.BytesIO()
            crop.save(buf, format="JPEG", quality=90)
            b = base64.b64encode(buf.getvalue()).decode("ascii")
            crops.append({"id": bid, "label": label,
                         "cropDataUrl": f"data:image/jpeg;base64,{b}"})

        # analyze patterns
        t1 = time.perf_counter()
        patterns = ai_client.analyze_batch(crops, max_concurrency=3)
        analyze_ms = (time.perf_counter() - t1) * 1000.0

        # create features and score
        t2 = time.perf_counter()
        features = create_outfit_features(seg, patterns, outfit_id)
        extraction_ms = (time.perf_counter() - t2) * 1000.0

        t3 = time.perf_counter()
        score = score_outfit(features)
        scoring_ms = (time.perf_counter() - t3) * 1000.0

        resp: Dict[str, Any] = {
            "segmentation": seg,
            "patterns": patterns,
            "features": features,
            "score": score,
        }

        if want_profile:
            resp["profiling"] = {
                "detect_ms": round(detect_ms, 2),
                "analyze_ms": round(analyze_ms, 2),
                "extraction_ms": round(extraction_ms, 2),
                "scoring_ms": round(scoring_ms, 2),
            }

        # record combined process profiling
        try:
            record_profile({
                "type": "process_image",
                "detect_ms": round(detect_ms, 2),
                "analyze_ms": round(analyze_ms, 2),
                "extraction_ms": round(extraction_ms, 2),
                "scoring_ms": round(scoring_ms, 2),
                "items": len(patterns),
            })
        except Exception:
            pass

        return jsonify(resp), 200
    except Exception as e:
        return jsonify({"error": f"Process failed: {e}"}), 500


def segment_frame(arr_rgb: np.ndarray, srcW: int, srcH: int) -> dict:
    Hd, Wd = arr_rgb.shape[:2]

    t0 = time.perf_counter()
    arr_rgb_for_det = bg_blur.apply(arr_rgb)
    t_blur = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    dets = detector.predict(arr_rgb_for_det)
    t_det = (time.perf_counter() - t1) * 1000.0

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

    # Remove conflicting garment detections (trousers vs shorts, etc)
    items = _deduplicate_conflicting_garments(items)

    # Filter overlapping detection (>70% IoU), keep higher confidence
    items = _filter_overlapping_items(items, iou_threshold=0.70)

    # return the **video-native** size
    profiling = {"bg_blur_ms": round(t_blur, 2), "detection_ms": round(
        t_det, 2), "total_ms": round(t_blur + t_det, 2)}
    # record segment profiling
    try:
        record_profile({"type": "segment", "bg_blur_ms": round(t_blur, 2), "detection_ms": round(
            t_det, 2), "total_ms": round(t_blur + t_det, 2), "items": len(items)})
    except Exception:
        pass

    return {"width": srcW, "height": srcH, "items": items, "profiling": profiling}


def _deduplicate_conflicting_garments(items: List[Dict]) -> List[Dict]:
    """
    Remove conflicting garment detections (e.g., trousers + shorts).
    When conflicting items are detected, favor more specific categories:
    - shorts, skirt > trousers
    - short sleeve top, sleeveless top > long sleeve top
    """
    if not items:
        return items

    # Define conflicting garment groups with preference order (higher index = more favored)
    conflict_groups = [
        [
            ("trousers", 0),
            ("shorts", 2),
            ("skirt", 2),
        ],
        [
            ("long_sleeve_top", 0),
            ("short_sleeve_top", 1),
        ],
    ]

    def get_conflict_group_and_priority(label: str) -> tuple:
        """Return (conflict_group, priority) or (None, 0)."""
        label_lower = label.lower()
        for group in conflict_groups:
            for garment_name, priority in group:
                if label_lower in garment_name or garment_name in label_lower:
                    return (group, priority)
        return (None, 0)

    kept = []
    removed_indices = set()

    for i, item in enumerate(items):
        if i in removed_indices:
            continue

        label_i = item.get("label", "").lower()
        conf_i = item.get("score", 0)
        conflict_group_i, priority_i = get_conflict_group_and_priority(label_i)

        if not conflict_group_i:
            kept.append(item)
            continue

        # Check for conflicts with other items
        should_skip_current = False
        for j, other in enumerate(items):
            if j <= i or j in removed_indices:
                continue

            label_j = other.get("label", "").lower()
            conflict_group_j, priority_j = get_conflict_group_and_priority(
                label_j)

            # If both are in the same conflict group
            if conflict_group_i == conflict_group_j:
                iou = compute_iou(item["bbox"], other["bbox"])
                # If IoU > 40%, they're likely overlapping detections
                if iou > 0.40:
                    conf_j = other.get("score", 0)

                    # Decision logic:
                    # 1. Favor higher priority (more specific category)
                    # 2. If same priority, favor higher confidence
                    if priority_i > priority_j:
                        # Current item is more specific, remove the other
                        removed_indices.add(j)
                    elif priority_j > priority_i:
                        # Other item is more specific, remove current
                        should_skip_current = True
                        break
                    else:
                        # Same priority, keep higher confidence
                        if conf_i >= conf_j:
                            removed_indices.add(j)
                        else:
                            should_skip_current = True
                            break

        if not should_skip_current:
            kept.append(item)
        else:
            removed_indices.add(i)

    return kept


def _filter_overlapping_items(items: List[Dict], iou_threshold: float = 0.70) -> List[Dict]:
    """Remove items with >iou_threshold overlap, keeping the one with higher confidence."""
    if not items:
        return items

    # Sort by score descending
    sorted_items = sorted(
        items, key=lambda it: it.get("score", 0), reverse=True)
    kept = []

    for item in sorted_items:
        # Check if this item overlaps significantly with any kept item
        overlaps_with_kept = False
        for kept_item in kept:
            iou = compute_iou(item["bbox"], kept_item["bbox"])
            if iou > iou_threshold:
                overlaps_with_kept = True
                break

        if not overlaps_with_kept:
            kept.append(item)

    return kept


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
        t0 = time.perf_counter()
        results = ai_client.analyze_batch(clean, max_concurrency=3)
        analyze_ms = (time.perf_counter() - t0) * 1000.0
        print(results)
        # Emit results as before for compatibility
        emit("patterns", results)
        # Also emit profiling info separately so the client can monitor latency
        emit("patterns_profiling", {"analyze_ms": round(
            analyze_ms, 2), "items": len(results)})
        # record analyze profiling
        try:
            record_profile({"type": "analyze_patterns", "analyze_ms": round(
                analyze_ms, 2), "items": len(results)})
        except Exception:
            pass
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
        emit("patterns_profiling", {"analyze_ms": 0.0, "items": len(fallback)})
        try:
            record_profile({"type": "analyze_patterns",
                           "analyze_ms": 0.0, "items": len(fallback)})
        except Exception:
            pass


@app.route("/api/style/score", methods=["POST"])
def api_style_score():
    """
    POST /api/style/score

    Body: OutfitFeatures (JSON)
    Returns: StyleScore (JSON)

    Idempotent: Same input → same output.
    """
    try:
        req_start = time.perf_counter()
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        # Validate required fields
        required_fields = ["outfitId", "garments", "colorClusters",
                           "thirdsArea", "domainZ", "extractionVersion"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({"error": f"Missing required fields: {missing}"}), 400

        # Support two modes:
        # 1) Caller provides full OutfitFeatures (backwards compatible)
        # 2) Caller provides `segmentation` + `patterns` and we build features server-side
        want_profile = bool(request.args.get("profile") ==
                            "1" or data.get("profile", False))

        if all(k in data for k in ("outfitId", "garments", "colorClusters", "thirdsArea", "domainZ", "extractionVersion")):
            features: OutfitFeatures = {
                "outfitId": str(data["outfitId"]),
                "garments": data["garments"],
                "colorClusters": data["colorClusters"],
                "thirdsArea": data["thirdsArea"],
                "domainZ": data["domainZ"],
                "body": data.get("body"),
                "extractionVersion": str(data["extractionVersion"]),
            }
        elif data.get("segmentation") and isinstance(data.get("patterns"), list):
            # build features server-side
            features = create_outfit_features(
                data["segmentation"], data["patterns"], data.get("outfitId"))
        else:
            return jsonify({"error": "Missing or malformed feature data"}), 400

        # Score the outfit and capture scoring latency
        t0 = time.perf_counter()
        result = score_outfit(features)
        scoring_ms = (time.perf_counter() - t0) * 1000.0

        # attach profiling into debug to avoid breaking clients that expect the score shape
        try:
            if isinstance(result.get("debug"), dict):
                result["debug"]["profiling"] = {
                    "scoring_ms": round(scoring_ms, 2)}
            else:
                result["debug"] = {"profiling": {
                    "scoring_ms": round(scoring_ms, 2)}}
        except Exception:
            result["debug"] = {"profiling": {
                "scoring_ms": round(scoring_ms, 2)}}

        if want_profile:
            # add api-level latency too (measured for this endpoint)
            api_ms = (time.perf_counter() - req_start) * 1000.0
            result["debug"]["profiling"]["api_ms"] = round(api_ms, 2)

        # record profiling
        try:
            record_profile({"type": "style_score", "scoring_ms": round(scoring_ms, 2), "api_ms": round(
                api_ms, 2) if want_profile else None, "items": len(features.get("garments", []))})
        except Exception:
            pass

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Scoring failed: {str(e)}"}), 500


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
