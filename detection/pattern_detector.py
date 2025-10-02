import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import cv2
import numpy as np
from typing import List, Tuple, Optional

class AlexNetPatternDetector:
    """
    Wraps the trained AlexNet model for cloth pattern classification.
    It handles model loading, image preprocessing, and pattern prediction
    from a cropped region of a frame.
    """
    
    # Transformations for inference (must match validation set preprocessing)
    INFERENCE_TRANSFORMS = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Dimensions for the crop area (200x200 pixel center mass)
    CROP_SIZE = 200

    def __init__(self, model_path, class_names: List[str], device: str = "cpu"):
        self.class_names = class_names
        self.device = device
        self.model = self._load_model(model_path, len(class_names), device)

    def _load_model(self, model_path, num_classes: int, device: str):
        """Initializes and loads the trained AlexNet model state."""
        try:
            # 1. Instantiate the pre-trained architecture
            model = models.alexnet(weights='AlexNet_Weights.IMAGENET1K_V1')
            
            # 2. Modify the final classification layer
            num_ftrs = model.classifier[6].in_features
            model.classifier[6] = nn.Linear(num_ftrs, num_classes)

            # 3. Load the custom weights
            model.load_state_dict(torch.load(model_path, map_location=device))
            model.eval() # Set model to evaluation mode
            model.to(device)
            print("AlexNet Pattern Detector loaded successfully.")
            return model
        except FileNotFoundError:
            print(f"Error: AlexNet model not found at {model_path}. Pattern detection disabled.")
            return None
        except Exception as e:
            print(f"Error loading AlexNet model: {e}")
            return None

    def predict_from_bbox(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> str:
        """
        Crops a 200x200 region around the center of the bounding box and predicts the pattern.

        :param frame: The full input image (BGR NumPy array).
        :param bbox: The bounding box (x1, y1, x2, y2).
        :return: The predicted pattern class name or an error message.
        """
        if self.model is None:
            return "No model"

        x1, y1, x2, y2 = bbox
        
        # 1. Calculate the center of the bounding box
        center_x, center_y = int((x1 + x2) / 2), int((y1 + y2) / 2)
        
        # 2. Define the fixed-size crop area (200x200)
        half_crop = self.CROP_SIZE // 2
        
        crop_x1 = max(0, center_x - half_crop)
        crop_y1 = max(0, center_y - half_crop)
        crop_x2 = min(frame.shape[1], center_x + half_crop)
        crop_y2 = min(frame.shape[0], center_y + half_crop)

        # 3. Crop the image region
        if crop_x2 > crop_x1 and crop_y2 > crop_y1:
            cropped_image = frame[crop_y1:crop_y2, crop_x1:crop_x2]
            
            # Convert the cropped cv2 image (BGR NumPy) to PIL for transformations
            pil_image = Image.fromarray(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB))
            
            # 4. Preprocess and prepare tensor
            image_tensor = self.INFERENCE_TRANSFORMS(pil_image).unsqueeze(0).to(self.device)
            
            # 5. Inference
            with torch.no_grad():
                output = self.model(image_tensor)
                _, predicted_class_idx = torch.max(output, 1)
                predicted_pattern = self.class_names[predicted_class_idx.item()]
                
            return predicted_pattern
        
        return "Crop Invalid"
