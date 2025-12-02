"""
Real image-based feature extraction for garments.
Extracts colors, texture, gloss, and patterns from actual image data.
"""

from __future__ import annotations
import math
import numpy as np
from typing import Any
from PIL import Image
import base64
import io

try:
    import cv2
except ImportError:
    cv2 = None


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """
    Convert RGB image (0-255) to LAB color space.
    
    Args:
        rgb: np.ndarray of shape (H, W, 3) with values in [0, 255]
    
    Returns:
        LAB image with L in [0, 100], a and b in [-127, 127]
    """
    # Normalize to [0, 1]
    rgb_norm = rgb.astype(np.float32) / 255.0
    
    # Apply gamma correction (inverse sRGB)
    mask = rgb_norm > 0.04045
    rgb_linear = np.where(
        mask,
        np.power((rgb_norm + 0.055) / 1.055, 2.4),
        rgb_norm / 12.92
    )
    
    # RGB to XYZ
    # Using sRGB D65 standard transformation matrix
    M = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ])
    
    # Reshape for matrix multiplication
    h, w = rgb_linear.shape[:2]
    rgb_reshaped = rgb_linear.reshape(-1, 3)
    xyz = np.dot(rgb_reshaped, M.T).reshape(h, w, 3)
    
    # Reference white point D65
    ref_white = np.array([0.95047, 1.00000, 1.08883])
    xyz_norm = xyz / ref_white
    
    # XYZ to LAB
    delta = 6.0 / 29.0
    mask = xyz_norm > delta ** 3
    f = np.where(
        mask,
        np.power(xyz_norm, 1.0 / 3.0),
        xyz_norm / (3.0 * delta ** 2) + 4.0 / 29.0
    )
    
    L = 116.0 * f[:, :, 1] - 16.0
    a = 500.0 * (f[:, :, 0] - f[:, :, 1])
    b = 200.0 * (f[:, :, 1] - f[:, :, 2])
    
    lab = np.stack([L, a, b], axis=-1)
    return lab


def extract_dominant_colors(
    img_array: np.ndarray,
    n_clusters: int = 5,
    max_samples: int = 10000
) -> list[tuple[float, float, float]]:
    """
    Extract dominant colors from an image using k-means clustering.
    
    Args:
        img_array: RGB image (H, W, 3) with values in [0, 255]
        n_clusters: Number of color clusters to extract
        max_samples: Max pixels to use for k-means (for speed)
    
    Returns:
        List of (L, a, b) tuples sorted by frequency (descending)
    """
    if img_array.size == 0:
        return [(60.0, 0.0, 0.0)]
    
    # Convert to LAB
    lab_img = rgb_to_lab(img_array)
    
    # Sample pixels (for speed on large images)
    h, w = lab_img.shape[:2]
    n_pixels = h * w
    
    if n_pixels > max_samples:
        # Random sampling
        indices = np.random.choice(n_pixels, max_samples, replace=False)
        pixels = lab_img.reshape(-1, 3)[indices]
    else:
        pixels = lab_img.reshape(-1, 3)
    
    # K-means clustering (manual simple implementation)
    n_clusters = min(n_clusters, len(pixels))
    
    # Initialize centroids randomly
    np.random.seed(42)  # Deterministic
    init_idx = np.random.choice(len(pixels), n_clusters, replace=False)
    centroids = pixels[init_idx].copy().astype(np.float32)
    
    # K-means iterations
    for _ in range(10):  # 10 iterations usually sufficient
        # Assign clusters
        distances = np.linalg.norm(
            pixels[:, None, :] - centroids[None, :, :],
            axis=2
        )  # (n_pixels, n_clusters)
        labels = np.argmin(distances, axis=1)
        
        # Update centroids
        for k in range(n_clusters):
            mask = labels == k
            if np.any(mask):
                centroids[k] = pixels[mask].mean(axis=0)
    
    # Assign final clusters
    distances = np.linalg.norm(
        pixels[:, None, :] - centroids[None, :, :],
        axis=2
    )
    labels = np.argmin(distances, axis=1)
    
    # Count frequency
    counts = np.bincount(labels, minlength=n_clusters)
    
    # Sort by frequency descending
    sorted_idx = np.argsort(-counts)
    
    colors = []
    for idx in sorted_idx:
        if counts[idx] > 0:
            lab = centroids[idx]
            colors.append((float(lab[0]), float(lab[1]), float(lab[2])))
    
    return colors


def compute_color_variance(img_array: np.ndarray) -> float:
    """
    Compute hue variance in image (how diverse are the colors).
    
    Returns:
        Variance value (higher = more diverse)
    """
    if img_array.size == 0:
        return 0.0
    
    lab_img = rgb_to_lab(img_array)
    
    # Sample pixels
    h, w = lab_img.shape[:2]
    pixels = lab_img.reshape(-1, 3)
    
    if len(pixels) > 5000:
        indices = np.random.choice(len(pixels), 5000, replace=False)
        pixels = pixels[indices]
    
    # Variance on a,b (hue) channels
    ab = pixels[:, 1:]  # (n, 2)
    variance = np.var(ab)
    
    return float(variance)


def estimate_gloss_index(img_array: np.ndarray) -> float:
    """
    Estimate glossiness (shine) from image.
    High values = glossy (leather, satin, silk)
    Low values = matte (cotton, wool)
    
    Uses: brightness hotspots, edge sharpness, saturation patterns
    
    Returns:
        Gloss index in [0, 1]
    """
    if img_array.size == 0:
        return 0.1
    
    # Convert to grayscale for brightness analysis
    gray = np.mean(img_array.astype(np.float32), axis=2)
    
    # Find bright regions (potential specular highlights)
    mean_brightness = np.mean(gray)
    std_brightness = np.std(gray)
    
    if std_brightness < 1:
        # Very uniform -> matte
        return 0.1
    
    # High brightness with sharp transitions = shiny
    bright_pixels = np.sum(gray > (mean_brightness + 2 * std_brightness))
    bright_ratio = bright_pixels / gray.size
    
    # Edge detection (sharp edges often indicate gloss)
    if cv2 is not None:
        edges = cv2.Canny(np.uint8(gray), 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
    else:
        # Fallback: simple gradient-based edge detection
        gx = np.abs(np.diff(gray, axis=1))
        gy = np.abs(np.diff(gray, axis=0))
        edge_density = np.mean(np.concatenate([gx.flatten(), gy.flatten()]) > 10)
    
    # Combine factors
    gloss = 0.4 * min(bright_ratio * 3, 1.0) + 0.6 * min(edge_density * 2, 1.0)
    gloss = float(np.clip(gloss, 0.0, 1.0))
    
    return gloss


def infer_material_from_image(
    img_array: np.ndarray,
    label: str = ""
) -> str:
    """
    Infer material from image appearance, combined with label hints.
    
    Returns:
        Material type string
    """
    # Start with label-based heuristic
    label_lower = (label or "").lower()
    if any(x in label_lower for x in ("denim", "jean")):
        return "denim"
    if "leather" in label_lower:
        return "leather"
    if "wool" in label_lower:
        return "wool"
    if "silk" in label_lower:
        return "silk"
    if "satin" in label_lower:
        return "satin"
    if "knit" in label_lower:
        return "knit"
    
    # Refine with image analysis
    gloss = estimate_gloss_index(img_array)
    
    # Estimate texture roughness
    gray = np.mean(img_array.astype(np.float32), axis=2)
    
    # High-frequency detail = rough texture (cotton, wool)
    if cv2 is not None:
        laplacian = cv2.Laplacian(np.uint8(gray), cv2.CV_32F)
        roughness = np.mean(np.abs(laplacian))
    else:
        roughness = 0.5
    
    # Decision tree
    if gloss > 0.7:
        return "satin"  # glossy, probably satin/silk-like
    if gloss > 0.6:
        return "leather"  # quite shiny
    if roughness > 5:
        return "wool"  # rough texture
    if roughness > 2:
        return "knit"  # moderate roughness
    
    return "cotton"  # default


def estimate_pattern_strength(
    img_array: np.ndarray,
    pattern_type: str = "none"
) -> float:
    """
    Estimate pattern intensity based on color/texture variance.
    
    Args:
        img_array: Garment crop
        pattern_type: Pattern class (from detector)
    
    Returns:
        Pattern strength in [0, 1]
    """
    if img_array.size == 0 or pattern_type == "none":
        return 0.0
    
    lab_img = rgb_to_lab(img_array)
    
    # For patterned fabrics, there's high variance in color space
    # Sample pixels
    pixels = lab_img.reshape(-1, 3)
    if len(pixels) > 5000:
        indices = np.random.choice(len(pixels), 5000, replace=False)
        pixels = pixels[indices]
    
    # Color variance (how different are adjacent pixels)
    h, w = lab_img.shape[:2]
    lab_reshaped = lab_img.reshape(h, w, 3)
    
    # Compute local color differences
    if h > 1 and w > 1:
        dy = np.abs(np.diff(lab_reshaped, axis=0, n=1)).mean()
        dx = np.abs(np.diff(lab_reshaped, axis=1, n=1)).mean()
        local_variance = (dy + dx) / 2.0
    else:
        local_variance = 0.0
    
    # Normalize: typical solid garment has variance ~5-10
    # typical patterned garment has variance ~20-40
    strength = min(local_variance / 30.0, 1.0)
    
    return float(strength)


def decode_image_from_base64(dataUrl: str) -> np.ndarray | None:
    """
    Decode image from data URL string.
    
    Args:
        dataUrl: "data:image/jpeg;base64,..." or similar
    
    Returns:
        RGB image as np.ndarray, or None on error
    """
    try:
        if not dataUrl.startswith("data:image/"):
            return None
        
        # Split header and data
        header, data = dataUrl.split(",", 1)
        
        # Decode base64
        img_bytes = base64.b64decode(data)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        
        return np.array(img)
    except Exception:
        return None


