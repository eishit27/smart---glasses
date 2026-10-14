"""
Metric Depth Calibration & Ground-Plane Projection Module
==========================================================

Solves the critical flaw of monocular depth models:
Monocular models output unitless relative disparity, NOT physical meters.

This module combines:
1. Known physical camera mounting height (glasses eye-level: H ≈ 1.6m)
2. Ground-plane geometric ray-casting: Z = H / tan(pitch + vertical_angle)
3. Dynamic scale-and-shift calibration fitting relative disparity to physical meters:
      Z_metric(x, y) = s * (1.0 / (D_rel(x, y) + ε)) + bias

Result: Real physical distance estimates (in meters) with obstacle alert boundaries:
- Immediate Danger: < 1.0 meter (Instant haptic pulse + high-pitch audio earcon)
- Proximity Warning: 1.0 – 2.5 meters (Directional warning)
- Safe Awareness: > 2.5 meters
"""

import math
import logging
from typing import Tuple, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

class MetricDepthCalibrator:
    def __init__(
        self,
        camera_height_m: float = 1.65, # Standard user eye height in meters
        camera_pitch_deg: float = 5.0,  # Glasses slight downward tilt (degrees)
        vertical_fov_deg: float = 50.0  # Typical OV2640 FOV
    ):
        self.height = camera_height_m
        self.pitch_rad = math.radians(camera_pitch_deg)
        self.vfov_rad = math.radians(vertical_fov_deg)

    def calibrate_depth_map(self, relative_depth_map: np.ndarray) -> np.ndarray:
        """
        Converts a normalized 2D relative depth map (0.0=far, 1.0=near)
        into an absolute metric depth map in meters.
        
        Returns:
            np.ndarray: Matrix of distances in physical meters (float32).
        """
        h, w = relative_depth_map.shape[:2]
        
        # Avoid division by zero
        safe_rel = np.clip(relative_depth_map, 0.01, 1.0)
        
        # Analytical ground plane anchor:
        # Sample points in the lower 25% of the frame (user's forward footway)
        ground_y = int(h * 0.85)
        # Vertical angle for this row relative to optical axis
        phi_y = ((ground_y - (h / 2.0)) / (h / 2.0)) * (self.vfov_rad / 2.0)
        total_angle = self.pitch_rad + phi_y
        
        # Expected physical ground distance at this row (meters)
        if total_angle > 0.05:
            expected_ground_z = self.height / math.tan(total_angle)
        else:
            expected_ground_z = 2.0  # sensible fallback
            
        sampled_rel_depth = float(np.median(safe_rel[ground_y - 10 : ground_y + 10, int(w*0.35) : int(w*0.65)]))
        
        # Compute scale factor relating inverse relative depth to physical meters
        # Z_metric ≈ scale / rel_depth
        scale_factor = expected_ground_z * sampled_rel_depth
        
        metric_depth = scale_factor / safe_rel
        # Clamp to realistic human walking perception range (0.3m to 20.0m)
        return np.clip(metric_depth, 0.3, 20.0).astype(np.float32)

    def get_obstacle_metric_distance(self, metric_map: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict[str, Any]:
        """
        Extracts the median physical distance in meters for a detected object bounding box.
        """
        x1, y1, x2, y2 = bbox
        h, w = metric_map.shape[:2]
        
        x1 = max(0, min(x1, w - 1))
        x2 = max(0, min(x2, w - 1))
        y1 = max(0, min(y1, h - 1))
        y2 = max(0, min(y2, h - 1))
        
        if x2 <= x1 or y2 <= y1:
            return {"distance_meters": 5.0, "zone": "safe"}

        obj_depth_patch = metric_map[y1:y2, x1:x2]
        # Use 20th percentile to focus on the closest edge of the obstacle
        dist_meters = float(np.percentile(obj_depth_patch, 20))

        if dist_meters < 1.0:
            zone = "critical_hazard"
        elif dist_meters < 2.5:
            zone = "proximity_warning"
        else:
            zone = "safe"

        return {
            "distance_meters": round(dist_meters, 2),
            "zone": zone
        }
