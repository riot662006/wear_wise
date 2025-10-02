from pathlib import Path
import torch

# Window
MAIN_WIN = "Smart Mirror (MVP)"

# Model Configurations
CLOTHE_SEG_MODEL_PATH = Path("models/yolov8n.pt")  # <-- update if needed
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
IMGSZ = 960        # YOLO inference size (try 640/768/960/1280)
CONF_THRESH = 0.25 # detection confidence

PATTERN_MODEL_PATH = Path('models/alexnet_pattern_model.pth') # Path to your trained AlexNet weights
PATTERN_CLASS_NAMES = ["checkered", "dotted", "floral", "solid", "striped", "zig_zag"]

# Background
BG_BLUR_KSIZE = (55, 55)

# Keys
KEY_QUIT = ("q", 27)   # q or ESC
KEY_RESET = "r"
KEY_GRAYSCALE = "g"
KEY_TOGGLE_BOXES = "b"

# Camera
CAM_INDEX = 0
CAP_WIDTH = 1280  # try 1920
CAP_HEIGHT = 720  # try 1080
