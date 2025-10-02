import cv2
import numpy as np
import mediapipe as mp
import pyautogui

from config import *
from detection.pattern_detector import AlexNetPatternDetector
from detection.yolo_detector import YoloClothesDetector
from visualization.draw import draw_detections, draw_hud
from utils.image import letterbox_resize
from ui.slider import SliderManager, SliderSpec

# Sliders
sliders = [
    SliderSpec("MaskTh", 0.0, 1.0, 0.1, step=0.01),
    SliderSpec("Conf", 0.0, 1.0, CONF_THRESH, step=0.01),  # live conf control
]

# Window & screen
SCREEN_SIZE = pyautogui.size()
cv2.namedWindow(MAIN_WIN, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(MAIN_WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# MediaPipe
mp_selfie = mp.solutions.selfie_segmentation
mp_pose = mp.solutions.pose


def main():
    # Sliders
    sm = SliderManager(MAIN_WIN)
    sm.add_many(sliders)

    # Camera
    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_HEIGHT)

    if not cap.isOpened():
        print("Camera not found")
        return

    # Detector
    detector = YoloClothesDetector(
        weights_path=CLOTHE_SEG_MODEL_PATH,
        device=DEVICE,
        imgsz=IMGSZ,
        conf=CONF_THRESH
    )
    yolo_class_names = detector.class_names

    pattern_detector = AlexNetPatternDetector(PATTERN_MODEL_PATH, PATTERN_CLASS_NAMES, DEVICE)

    # Toggles
    grayscale = False
    show_boxes = True

    with mp_selfie.SelfieSegmentation(model_selection=1) as seg, mp_pose.Pose(model_complexity=1) as pose:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Camera not found")
                break

            frame = cv2.flip(frame, 1)  # mirror

            # Background processing
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = seg.process(rgb)
            condition = np.stack((results.segmentation_mask,)
                                 * 3, axis=-1) > float(sm.get("MaskTh"))
            bg_blur = cv2.GaussianBlur(frame, BG_BLUR_KSIZE, 0)
            view = np.where(condition, frame, bg_blur)

            # Optional grayscale (keep 3 channels for YOLO pipeline consistency)
            if grayscale:
                gray = cv2.cvtColor(view, cv2.COLOR_BGR2GRAY)
                view_for_det = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            else:
                view_for_det = view

            # Update detector conf from slider
            detector.conf = float(sm.get("Conf"))

            # Detect on original-sized view_for_det
            rects = detector.predict(view_for_det)

            # Draw boxes
            if show_boxes and rects:
                view = draw_detections(view, rects, yolo_class_names)

                # --- NEW: Pattern Prediction Loop (Using the class method) ---
                for rect in rects:
                    x1, y1, x2, y2, conf, cls = rect
                    
                    bbox = (x1, y1, x2, y2)
                    predicted_pattern = pattern_detector.predict_from_bbox(view_for_det, bbox)
                    
                    # Draw pattern label
                    text = f"Pattern: {predicted_pattern}"
                    text_x = int(x1)
                    
                    # FIX: Offset the pattern text below the YOLO detection label.
                    # Assuming the YOLO label is around 20-25 pixels high,
                    # we use an offset of 30 pixels from the top of the box.
                    yolo_label_offset = 30 
                    text_y = int(y1) + yolo_label_offset
                    
                    cv2.putText(view, text, (text_x, text_y), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                
               

            # HUD
            hud = f"Conf={detector.conf:.2f} Gray={grayscale} Boxes={show_boxes} ResCam={int(cap.get(3))}x{int(cap.get(4))} ImgSz={detector.imgsz}"
            view = draw_hud(view, hud)

            # Fullscreen scaling
            out = letterbox_resize(view, SCREEN_SIZE.width, SCREEN_SIZE.height)
            cv2.imshow(MAIN_WIN, out)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord(KEY_QUIT[0]), KEY_QUIT[1]):
                break
            elif key == ord(KEY_RESET):
                grayscale = False
                show_boxes = True
                sm.set("MaskTh", 0.1)
                sm.set("Conf", CONF_THRESH)
            elif key == ord(KEY_GRAYSCALE):
                grayscale = not grayscale
            elif key == ord(KEY_TOGGLE_BOXES):
                show_boxes = not show_boxes

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
