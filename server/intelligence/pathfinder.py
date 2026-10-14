"""
VisionAid Free-Space Corridor Pathfinder ("Virtual Guide Dog")
=============================================================

Transforms the device from a passive "obstacle shouter" into an active pathfinder.

Instead of just listing what's in the way, this module:
1. Calculates the widest, safest walkable corridor through the room or sidewalk
2. Computes the free space clearance depth (how many meters you can walk forward)
3. Directs the user along the path of least resistance:
   - "Straight path blocked. Turn slightly to 1 o'clock, clear for 5 meters."
   - "Safe walking corridor between 11 and 12 o'clock."
"""

import logging
from typing import Dict, List, Tuple, Any
import numpy as np

logger = logging.getLogger(__name__)

class FreeSpacePathfinder:
    def __init__(self, num_sectors: int = 5):
        # 5 angular sectors across 60° FOV:
        # Sector 0: 10 o'clock (Left)
        # Sector 1: 11 o'clock (Slight Left)
        # Sector 2: 12 o'clock (Center Ahead)
        # Sector 3: 1 o'clock  (Slight Right)
        # Sector 4: 2 o'clock  (Right)
        self.num_sectors = num_sectors
        self.sector_names = [
            "at 10 o'clock (on your left)",
            "at 11 o'clock (slight left)",
            "straight ahead (at 12 o'clock)",
            "at 1 o'clock (slight right)",
            "at 2 o'clock (on your right)"
        ]

    def find_navigable_corridor(
        self,
        frame_shape: Tuple[int, int],
        obstacles: List[Dict[str, Any]],
        metric_depth_map: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Analyzes forward space and identifies the best walking corridor.
        """
        h, w = frame_shape[:2]
        sector_width = w / self.num_sectors

        # Sector clearance depths (default 6.0m = open path)
        sector_clearance = [6.0] * self.num_sectors

        # Reduce sector clearance based on detected obstacles
        for obs in obstacles:
            bbox = obs.get('bbox', (0,0,0,0))
            dist = obs.get('distance_meters', 2.0)
            
            x1, y1, x2, y2 = bbox
            obj_cx = (x1 + x2) / 2.0
            
            # Find which sector this obstacle falls into
            sec_idx = int(obj_cx / sector_width)
            sec_idx = max(0, min(self.num_sectors - 1, sec_idx))

            # Update lowest clearance in that sector
            if dist < sector_clearance[sec_idx]:
                sector_clearance[sec_idx] = dist

        # Find sector with greatest clearance
        best_sector_idx = int(np.argmax(sector_clearance))
        best_clearance = sector_clearance[best_sector_idx]
        center_clearance = sector_clearance[2] # 12 o'clock (straight ahead)

        # Decide guidance
        if center_clearance >= 3.0:
            guidance = "Path is clear straight ahead."
            status = "clear_ahead"
            best_heading = "straight ahead"
        elif best_clearance >= 2.5 and best_sector_idx != 2:
            direction_name = self.sector_names[best_sector_idx]
            guidance = f"Direct path is restricted. Clear walking corridor {direction_name} for {best_clearance:.1f} meters."
            status = "divert_recommended"
            best_heading = direction_name
        elif best_clearance < 1.5:
            guidance = "Path is blocked on all sides. Please pause."
            status = "all_blocked"
            best_heading = "halt"
        else:
            guidance = f"Proceed with caution. Widest opening is {self.sector_names[best_sector_idx]}."
            status = "cautious_advance"
            best_heading = self.sector_names[best_sector_idx]

        return {
            "status": status,
            "best_sector": best_sector_idx,
            "best_heading": best_heading,
            "clearance_meters": round(best_clearance, 1),
            "spoken_guidance": guidance,
            "sector_clearances": [round(c, 1) for c in sector_clearance]
        }
