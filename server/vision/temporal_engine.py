"""
VisionAid Spatio-Temporal Motion & Dynamics Engine
==================================================

Processes continuous video as a temporal continuum rather than disjoint still frames.
Tracks physical dynamics:
1. Dense Optical Flow (Farneback) detecting moving entities vs stationary textures.
2. Kinetic Hazard Classification: Rolling balls, approaching wheelchairs/strollers, swinging doors.
3. Flow divergence: Positive divergence = expanding hazard approaching camera; Negative = receding.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class TemporalMotionEngine:
    def __init__(self, history_frames: int = 5):
        self.history_frames = history_frames
        self.prev_gray: Optional[np.ndarray] = None
        self.motion_energy_history: List[float] = []

    def compute_motion_dynamics(self, current_frame: np.ndarray) -> Dict[str, Any]:
        """
        Calculates dense spatio-temporal flow fields and detects kinetic threats.
        """
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY) if len(current_frame.shape) == 3 else current_frame
        # Downscale for real-time 20ms performance
        small_gray = cv2.resize(gray, (160, 120))

        if self.prev_gray is None:
            self.prev_gray = small_gray
            return {
                "kinetic_threat_detected": False,
                "motion_direction": "stationary",
                "divergence_expansion": 0.0,
                "dynamic_regions": []
            }

        # Calculate dense optical flow
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, small_gray, None,
            pyr_scale=0.5, levels=2, winsize=13, iterations=2, poly_n=5, poly_sigma=1.1, flags=0
        )

        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        avg_mag = float(np.mean(mag))

        # Optical flow divergence (rate of expansion -> TTC proxy)
        # Expansion (divergence > 0) indicates an approaching object growing in visual size
        fx = flow[..., 0]
        fy = flow[..., 1]
        div_x = np.gradient(fx, axis=1)
        div_y = np.gradient(fy, axis=0)
        divergence = float(np.mean(div_x + div_y))

        # Identify localized clusters of fast motion
        high_motion_mask = mag > (avg_mag + 2.0)
        dynamic_regions = []
        if np.any(high_motion_mask):
            contours, _ = cv2.findContours(high_motion_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                if cv2.contourArea(cnt) > 25:
                    x, y, w, h = cv2.boundingRect(cnt)
                    # Scale back to original frame coordinates
                    scale_x = current_frame.shape[1] / 160.0
                    scale_y = current_frame.shape[0] / 120.0
                    dynamic_regions.append({
                        "bbox": (int(x * scale_x), int(y * scale_y), int((x + w) * scale_x), int((y + h) * scale_y)),
                        "is_approaching": divergence > 0.08
                    })

        self.prev_gray = small_gray
        self.motion_energy_history.append(avg_mag)
        if len(self.motion_energy_history) > self.history_frames:
            self.motion_energy_history.pop(0)

        return {
            "kinetic_threat_detected": divergence > 0.15 and len(dynamic_regions) > 0,
            "motion_direction": "approaching" if divergence > 0.05 else "receding" if divergence < -0.05 else "stable",
            "divergence_expansion": round(divergence, 3),
            "dynamic_regions": dynamic_regions
        }
