"""
VisionAid Episodic Visual Memory Engine
=======================================

Gives the smart glasses persistent spatial memory of the user's surroundings.

Solves one of the biggest daily challenges for blind individuals:
"Where did I set down my phone / keys / wallet / mug / medicine?"

Features:
1. Tracks personal belongings continuously as they enter and leave view
2. Records spatial snapshot: location, surface (desk, counter, couch), clock direction, distance
3. "Find Object" query engine: Allows natural language questions:
   - "Where did I put my water bottle?"
   - "Did I leave my keys on the counter?"
   - "When did I last see my wallet?"
4. Guides the user's hands back to the lost object with tactile clock directions!
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

@dataclass
class MemoryItem:
    label: str
    last_seen_time: float
    clock_direction: str       # e.g. "at 10 o'clock"
    distance_meters: float     # e.g. 1.2
    surface_context: str       # e.g. "on the wooden desk", "next to the laptop"
    confidence: float
    bbox: Tuple[int, int, int, int]
    last_user_heading_deg: float = 0.0

class VisualWorkingMemory:
    """
    Episodic memory store maintaining real-time awareness of objects in the user's environment.
    """

    TRACKED_PERSONAL_ITEMS = {
        'cell phone', 'phone', 'keys', 'bottle', 'cup', 'mug',
        'wallet', 'laptop', 'backpack', 'handbag', 'book',
        'glasses', 'white cane', 'pill bottle', 'remote', 'bowl', 'plate'
    }

    def __init__(self, memory_retention_minutes: float = 45.0):
        self.retention_sec = memory_retention_minutes * 60.0
        # Map item label -> MemoryItem
        self.memory: Dict[str, MemoryItem] = {}

    def update_from_scene(
        self,
        detections: List[Dict[str, Any]],
        scene_context: str = ""
    ):
        """
        Ingests current frame detections and updates episodic memory.
        """
        now = time.time()
        
        for det in detections:
            label = det['label'].lower()
            
            # Check if this is a personal belonging we should remember
            matches = [item for item in self.TRACKED_PERSONAL_ITEMS if item in label]
            if not matches:
                continue
                
            canonical_item = matches[0]
            dist = det.get('distance_meters', 1.5)
            center_x = det.get('center_x', 0.5)
            
            # Compute clock position from horizontal coordinate
            # 0.0 (left) = 9 o'clock, 0.5 (center) = 12 o'clock, 1.0 (right) = 3 o'clock
            if center_x < 0.2:
                clock_pos = "at 9 o'clock (hard left)"
            elif center_x < 0.4:
                clock_pos = "at 10 o'clock (to your left)"
            elif center_x < 0.6:
                clock_pos = "at 12 o'clock (straight ahead)"
            elif center_x < 0.8:
                clock_pos = "at 2 o'clock (to your right)"
            else:
                clock_pos = "at 3 o'clock (hard right)"

            surface_hint = "on the surface in front of you"
            if "table" in scene_context or "desk" in scene_context:
                surface_hint = "on the table"
            elif "counter" in scene_context:
                surface_hint = "on the counter"

            self.memory[canonical_item] = MemoryItem(
                label=canonical_item,
                last_seen_time=now,
                clock_direction=clock_pos,
                distance_meters=dist,
                surface_context=surface_hint,
                confidence=det.get('confidence', 0.8),
                bbox=det.get('bbox', (0,0,0,0))
            )
            logger.debug(f"Memorized location of {canonical_item}: {clock_pos}, {dist:.1f}m")

        # Expire old memories
        self._prune_expired(now)

    def _prune_expired(self, current_time: float):
        expired = [k for k, v in self.memory.items() if (current_time - v.last_seen_time) > self.retention_sec]
        for k in expired:
            del self.memory[k]

    def find_item(self, query_text: str) -> Dict[str, Any]:
        """
        Answers "Where is my [item]?" with exact spatial and temporal directions.
        """
        now = time.time()
        query_lower = query_text.lower()

        # Find best matching tracked item
        matched_item = None
        for item_key, mem in self.memory.items():
            if item_key in query_lower:
                matched_item = mem
                break

        if not matched_item:
            # Check for synonyms (e.g. "cell" or "mobile" -> "phone")
            synonyms = {
                "mobile": "phone",
                "water": "bottle",
                "coffee": "cup",
                "cane": "white cane"
            }
            for syn, target in synonyms.items():
                if syn in query_lower and target in self.memory:
                    matched_item = self.memory[target]
                    break

        if not matched_item:
            return {
                "found": False,
                "message": f"I haven't seen that recently in your field of view."
            }

        elapsed_seconds = int(now - matched_item.last_seen_time)
        if elapsed_seconds < 60:
            time_str = "just a few seconds ago"
        elif elapsed_seconds < 120:
            time_str = "about a minute ago"
        else:
            time_str = f"about {elapsed_seconds // 60} minutes ago"

        spoken_guidance = (
            f"Your {matched_item.label} was seen {time_str} {matched_item.surface_context}, "
            f"{matched_item.clock_direction}, approximately {matched_item.distance_meters:.1f} meters away."
        )

        return {
            "found": True,
            "item": matched_item.label,
            "message": spoken_guidance,
            "clock_direction": matched_item.clock_direction,
            "distance_meters": matched_item.distance_meters,
            "seconds_ago": elapsed_seconds
        }
