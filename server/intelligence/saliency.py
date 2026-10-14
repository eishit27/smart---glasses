"""
VisionAid Cognitive Saliency & Attention Filter
===============================================

Prevents cognitive sensory overload for blind individuals.

Filters out irrelevant visual noise (ceiling lights, wall posters, background clouds)
and prioritizes high-salience accessibility affordances based on a 4-tier hierarchy:

Tier 1: Life Safety & Collision (Drop-offs, stairs, oncoming vehicles, head hazards)
Tier 2: Immediate Physical Affordances (Door handles, empty chairs, handrails)
Tier 3: Social Cues (People approaching, gestures, eye contact)
Tier 4: Environmental Context (Signage, room layout, ambiance)
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class CognitiveSaliencyFilter:
    TIER_1_HAZARDS = {
        'stairs_down', 'stairs_up', 'curb', 'head_hazard', 'ground_obstacle',
        'vehicle', 'car', 'truck', 'bus', 'motorcycle', 'bicycle'
    }

    TIER_2_AFFORDANCES = {
        'door', 'glass_door', 'chair', 'bench', 'pole_bollard', 'crosswalk', 'pedestrian_signal'
    }

    TIER_3_SOCIAL = {
        'person'
    }

    def prioritize_detections(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sorts detections by cognitive urgency and filters out low-signal background noise.
        """
        def get_urgency_score(item: Dict[str, Any]) -> float:
            label = item.get('label', '').lower()
            dist = item.get('distance_meters', 5.0)
            
            # Base score by tier
            if any(h in label for h in self.TIER_1_HAZARDS):
                base = 100.0
            elif any(a in label for a in self.TIER_2_AFFORDANCES):
                base = 60.0
            elif any(s in label for s in self.TIER_3_SOCIAL):
                base = 40.0
            else:
                base = 10.0

            # Distance proximity multiplier: closer = much higher urgency
            proximity_weight = max(0.0, (6.0 - dist) * 10.0)
            return base + proximity_weight

        # Sort descending by urgency
        sorted_items = sorted(detections, key=get_urgency_score, reverse=True)
        # Limit to top 3 highest-salience items so user isn't overwhelmed
        return sorted_items[:3]
