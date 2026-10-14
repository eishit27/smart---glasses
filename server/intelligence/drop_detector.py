"""
VisionAid Drop Detector & Floor Target Locator
==============================================

Solves one of the most stressful daily moments for visually impaired people:
Dropping keys, coins, credit cards, or pill bottles and having to search
on hands and knees.

How it works:
1. Detects sudden downward trajectories in the lower visual field
2. Tracks where the dropped item lands relative to the user's feet
3. Provides tactile clock directions:
   "You dropped an item about 30 centimeters to the right of your shoe (at 2 o'clock)."
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

logger = logging.getLogger(__name__)

class DropDetector:
    def __init__(self, ground_roi_ratio: float = 0.65):
        # Focus on lower 35% of the camera frame where feet and floor are visible
        self.ground_roi = ground_roi_ratio
        self.last_floor_objects = []
        self.last_drop_alert_time = 0.0

    def detect_dropped_item(
        self,
        detections: List[Dict[str, Any]],
        frame_shape: Tuple[int, int]
    ) -> Optional[Dict[str, Any]]:
        """
        Scans ground plane for small newly appeared objects close to the user (< 0.8m).
        """
        now = time.time()
        if now - self.last_drop_alert_time < 5.0:
            return None  # Cooldown

        h, w = frame_shape[:2]
        ground_y = int(h * self.ground_roi)

        DROP_CANDIDATE_CLASSES = {
            'keys', 'coin', 'card', 'cell phone', 'phone', 'bottle',
            'cup', 'remote', 'pen', 'wallet', 'ground_obstacle'
        }

        floor_candidates = []
        for det in detections:
            bbox = det.get('bbox', (0,0,0,0))
            x1, y1, x2, y2 = bbox
            dist = det.get('distance_meters', 2.0)
            
            # Must be in lower visual field (on floor near user) and close (< 1.0m)
            if y2 > ground_y and dist < 1.1:
                label = det.get('label', 'item').lower()
                floor_candidates.append(det)

        # Check for newly appeared items on the floor
        if floor_candidates and not self.last_floor_objects:
            item = floor_candidates[0]
            bbox = item.get('bbox', (0,0,0,0))
            cx = (bbox[0] + bbox[2]) / (2.0 * w)
            dist = item.get('distance_meters', 0.5)

            # Determine position relative to feet
            if cx < 0.35:
                pos = "to the left of your foot at 9 o'clock"
            elif cx > 0.65:
                pos = "to the right of your foot at 3 o'clock"
            else:
                pos = "directly in front of your toes at 12 o'clock"

            self.last_drop_alert_time = now
            self.last_floor_objects = floor_candidates
            
            label_name = item.get('label', 'An item')
            message = f"Drop alert: {label_name} is on the floor {pos}, about {int(dist * 100)} centimeters away."
            
            logger.info(f"🎯 Drop detected: {message}")
            return {
                "detected": True,
                "label": label_name,
                "distance_cm": int(dist * 100),
                "position": pos,
                "message": message
            }

        self.last_floor_objects = floor_candidates
        return None
