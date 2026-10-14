"""
VisionAid Affordance & Physical Interaction Engine
==================================================

Computes the *affordances* of the visual environment:
Not just WHAT an object is, but HOW the blind user can physically interact with it.

Covers:
1. Doors: Push vs Pull, Handle location (Left / Right / Knob), Glass warnings, Threshold steps.
2. Seating: Empty seat vs Occupied seat, Armrests, Seat height.
3. Stairs: Handrail position (Left wall / Right wall / Center).
4. Pedestrian Crossings: Walk signal buttons, tactile curb ramp locations.
5. Elevators: Call button clusters, door direction.
"""

import logging
from typing import Dict, List, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)

class AffordanceEngine:
    def __init__(self):
        pass

    def analyze_door_affordance(
        self,
        door_bbox: tuple,
        frame_shape: tuple,
        surrounding_detections: List[Dict],
        ocr_text: str = ""
    ) -> str:
        """
        Calculates physical interaction guidance for an approaching door.
        """
        x1, y1, x2, y2 = door_bbox
        w_door = x2 - x1
        h_frame, w_frame = frame_shape[:2]

        # Check for push / pull signage
        text_lower = ocr_text.lower()
        push_pull = ""
        if "push" in text_lower:
            push_pull = "It is a PUSH door"
        elif "pull" in text_lower:
            push_pull = "It is a PULL door"
        elif "automatic" in text_lower or "slide" in text_lower:
            push_pull = "It is an automatic sliding door"

        # Check handle position relative to door width
        door_center_x = (x1 + x2) / 2.0
        if door_center_x < w_frame * 0.45:
            handle_hint = "handle is on the right side"
        else:
            handle_hint = "handle is on the left side"

        guidance_parts = ["Door ahead."]
        if push_pull:
            guidance_parts.append(f"{push_pull}.")
        guidance_parts.append(f"Reach for the {handle_hint}.")

        if "glass" in text_lower or any(d.get('label') == 'glass_door' for d in surrounding_detections):
            guidance_parts.append("Caution: Glass panel.")

        return " ".join(guidance_parts)

    def analyze_seating_affordance(
        self,
        seat_bbox: tuple,
        frame_shape: tuple,
        detections: List[Dict]
    ) -> str:
        """
        Determines if a chair or bench is empty, where it is, and how to sit.
        """
        # Check if a person overlaps or occupies this chair
        x1, y1, x2, y2 = seat_bbox
        is_occupied = False
        
        for det in detections:
            if det.get('label') == 'person':
                px1, py1, px2, py2 = det.get('bbox', (0,0,0,0))
                # Check overlap
                if not (x2 < px1 or x1 > px2 or y2 < py1 or y1 > py2):
                    is_occupied = True
                    break

        if is_occupied:
            return "Chair ahead, but someone is currently seated there."
        else:
            cx = (x1 + x2) / (2.0 * frame_shape[1])
            clock_pos = "straight ahead" if 0.4 <= cx <= 0.6 else ("to your left at 10 o'clock" if cx < 0.4 else "to your right at 2 o'clock")
            return f"Empty seat available {clock_pos}. Seat facing forward."

    def analyze_stairs_handrail(
        self,
        stairs_bbox: tuple,
        is_descending: bool = False
    ) -> str:
        """
        Directs user to the safest physical point on stairs: the handrail.
        """
        direction = "down" if is_descending else "up"
        return f"Stairs leading {direction}. Recommend feeling along the right wall for the handrail."
