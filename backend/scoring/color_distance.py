"""
CIEDE2000 color distance calculation.
Implementation based on the CIEDE2000 standard.
"""

from __future__ import annotations
import math
import numpy as np


def delta_e_00(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """
    Calculate CIEDE2000 color difference between two LAB colors.
    
    Args:
        lab1: First color as (L, a, b)
        lab2: Second color as (L, a, b)
    
    Returns:
        CIEDE2000 delta E value
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    
    # Convert to numpy for easier computation
    L1, a1, b1 = float(L1), float(a1), float(b1)
    L2, a2, b2 = float(L2), float(a2), float(b2)
    
    # Calculate C*ab (chroma)
    C1 = math.sqrt(a1**2 + b1**2)
    C2 = math.sqrt(a2**2 + b2**2)
    C_avg = (C1 + C2) / 2.0
    
    # Calculate G (for chroma weighting)
    G = 0.5 * (1 - math.sqrt(C_avg**7 / (C_avg**7 + 25**7)))
    
    # Adjust a* values
    a1_prime = (1 + G) * a1
    a2_prime = (1 + G) * a2
    
    # Recalculate C* and h*
    C1_prime = math.sqrt(a1_prime**2 + b1**2)
    C2_prime = math.sqrt(a2_prime**2 + b2**2)
    
    h1_prime = math.atan2(b1, a1_prime) * 180.0 / math.pi
    h2_prime = math.atan2(b2, a2_prime) * 180.0 / math.pi
    
    # Normalize h to [0, 360)
    if h1_prime < 0:
        h1_prime += 360
    if h2_prime < 0:
        h2_prime += 360
    
    # Calculate delta values
    dL_prime = L2 - L1
    dC_prime = C2_prime - C1_prime
    
    # Calculate delta h
    if C1_prime * C2_prime == 0:
        dh_prime = 0
    elif abs(h2_prime - h1_prime) <= 180:
        dh_prime = h2_prime - h1_prime
    elif h2_prime - h1_prime > 180:
        dh_prime = h2_prime - h1_prime - 360
    else:
        dh_prime = h2_prime - h1_prime + 360
    
    dH_prime = 2 * math.sqrt(C1_prime * C2_prime) * math.sin(math.radians(dh_prime / 2.0))
    
    # Calculate average values
    L_avg_prime = (L1 + L2) / 2.0
    C_avg_prime = (C1_prime + C2_prime) / 2.0
    
    # Calculate h_avg_prime
    if C1_prime * C2_prime == 0:
        h_avg_prime = h1_prime + h2_prime
    elif abs(h2_prime - h1_prime) <= 180:
        h_avg_prime = (h1_prime + h2_prime) / 2.0
    elif abs(h2_prime - h1_prime) > 180 and (h1_prime + h2_prime) < 360:
        h_avg_prime = (h1_prime + h2_prime + 360) / 2.0
    else:
        h_avg_prime = (h1_prime + h2_prime - 360) / 2.0
    
    # Calculate T (hue rotation term)
    T = (1 - 0.17 * math.cos(math.radians(h_avg_prime - 30)) +
         0.24 * math.cos(math.radians(2 * h_avg_prime)) +
         0.32 * math.cos(math.radians(3 * h_avg_prime + 6)) -
         0.20 * math.cos(math.radians(4 * h_avg_prime - 63)))
    
    # Calculate weighting functions
    dTheta = 30 * math.exp(-((h_avg_prime - 275) / 25)**2)
    R_C = 2 * math.sqrt(C_avg_prime**7 / (C_avg_prime**7 + 25**7))
    R_T = -math.sin(math.radians(2 * dTheta)) * R_C
    
    # Calculate k_L, k_C, k_H (standard viewing conditions)
    k_L = 1.0
    k_C = 1.0
    k_H = 1.0
    
    # Calculate S_L, S_C, S_H
    S_L = 1 + (0.015 * (L_avg_prime - 50)**2) / math.sqrt(20 + (L_avg_prime - 50)**2)
    S_C = 1 + 0.045 * C_avg_prime
    S_H = 1 + 0.015 * C_avg_prime * T
    
    # Final calculation
    dE00 = math.sqrt(
        (dL_prime / (k_L * S_L))**2 +
        (dC_prime / (k_C * S_C))**2 +
        (dH_prime / (k_H * S_H))**2 +
        R_T * (dC_prime / (k_C * S_C)) * (dH_prime / (k_H * S_H))
    )
    
    return dE00

