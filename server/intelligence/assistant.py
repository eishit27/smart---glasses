"""
VisionAid Cognitive Assistant Coordinator
=========================================

The high-level intelligence core that makes the glasses "genuinely smart":

Unifies:
1. Episodic Visual Working Memory ("Where did I leave my keys/phone?")
2. Drop Detection & Floor Object Finder ("I dropped something near my feet")
3. Physical Affordances Engine (Push/Pull door handles, empty chairs, handrails)
4. Specialized Life Skills (Prescription Reader, Currency Identifier, Social Cues)
5. Free-Space Corridor Pathfinder ("Virtual Guide Dog")
6. Cognitive Saliency Filter (Zero clutter, maximum signal)
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np

from .visual_memory import VisualWorkingMemory
from .specialized_skills import SpecializedAccessibilitySkills
from .pathfinder import FreeSpacePathfinder
from .drop_detector import DropDetector
from .affordances import AffordanceEngine
from .saliency import CognitiveSaliencyFilter
from .cognitive_mind import (
    TrajectoryForesightEngine,
    TheoryOfMindSocialEngine,
    CognitiveChainOfThought,
    ProactiveInterventionPolicy,
)

logger = logging.getLogger(__name__)

class CognitiveAssistant:
    def __init__(self):
        self.memory = VisualWorkingMemory(memory_retention_minutes=45.0)
        self.skills = SpecializedAccessibilitySkills()
        self.pathfinder = FreeSpacePathfinder()
        self.drop_detector = DropDetector()
        self.affordance_engine = AffordanceEngine()
        self.saliency_filter = CognitiveSaliencyFilter()
        self.trajectory_engine = TrajectoryForesightEngine(history_window_seconds=2.0)
        self.social_engine = TheoryOfMindSocialEngine()
        self.intervention_policy = ProactiveInterventionPolicy(speech_cooldown_seconds=3.5)

    def update_world_state(
        self,
        detections: List[Dict[str, Any]],
        scene_summary: str = "",
        frame_shape: tuple = (480, 640),
        immediate_hazard_m: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Continuously updates visual memory, calculates predictive trajectories,
        evaluates human social intent, and applies the Proactive Intervention Policy
        to prevent audio clutter while ensuring life safety.
        """
        # Prioritize through saliency filter
        salient_detections = self.saliency_filter.prioritize_detections(detections)
        
        # Update episodic memory
        self.memory.update_from_scene(salient_detections, scene_summary)

        # Proactive Drop Detection check
        drop_event = self.drop_detector.detect_dropped_item(detections, frame_shape)

        # Predictive Trajectory Foresight (moving pedestrians, bikes, vehicles)
        urgent_trajectories = self.trajectory_engine.update_tracks(detections)

        # Social Intent Check
        social_intent = None
        persons = [d for d in detections if d.get('label') == 'person']
        if persons:
            p = persons[0]
            depth_m = p.get('distance_m', 2.0)
            social_intent = self.social_engine.evaluate_person_intent(
                p.get('bbox', [0, 0, 0, 0]), frame_shape, depth_m, context_objects=detections
            )

        # Apply Proactive Intervention Policy
        decision = self.intervention_policy.decide_intervention(
            urgent_trajectories=urgent_trajectories,
            drop_detected=drop_event,
            social_intent=social_intent,
            immediate_hazard_meters=immediate_hazard_m
        )

        return decision

    async def answer_smart_query(
        self,
        query: str,
        current_frame: np.ndarray,
        current_detections: List[Dict[str, Any]],
        ocr_text: str = "",
        vlm_engine: Optional[Any] = None
    ) -> str:
        """
        Intelligently resolves complex user queries using the appropriate cognitive skill.
        """
        q = query.lower().strip()
        logger.info(f"Processing cognitive query: '{q}'")

        # ── 1. Lost Object / Episodic Memory Query ─────────────────────────
        # "Where is my...", "Where did I put...", "Find my..."
        if any(trigger in q for trigger in ["where is", "where did", "find my", "locate my", "where's my"]):
            mem_result = self.memory.find_item(q)
            return mem_result["message"]

        # ── 2. Dropped Object Query ─────────────────────────────────────────
        # "Did I drop something?", "Where did it fall?"
        if any(trigger in q for trigger in ["drop", "dropped", "fell", "floor"]):
            drop_res = self.drop_detector.detect_dropped_item(current_detections, current_frame.shape)
            if drop_res and drop_res.get("message"):
                return drop_res["message"]
            return "I don't see any recently dropped items on the floor near your feet."

        # ── 3. Physical Affordance Query (Doors, Chairs, Stairs) ────────────
        # "How do I open this door?", "Is this chair empty?", "Where is the handrail?"
        if "door" in q:
            doors = [d for d in current_detections if 'door' in d.get('label', '')]
            if doors:
                return self.affordance_engine.analyze_door_affordance(
                    doors[0]['bbox'], current_frame.shape, current_detections, ocr_text
                )
            return "I don't see a door directly in front of you."

        if any(trigger in q for trigger in ["chair", "seat", "sit", "bench"]):
            chairs = [d for d in current_detections if d.get('label') in ['chair', 'bench']]
            if chairs:
                return self.affordance_engine.analyze_seating_affordance(
                    chairs[0]['bbox'], current_frame.shape, current_detections
                )
            return "No empty chairs or benches detected in front of you."

        # ── 4. Medication / Prescription Intelligence ───────────────────────
        if any(trigger in q for trigger in ["medicine", "prescription", "pill", "dosage", "drug"]):
            med_info = self.skills.parse_medication_label(ocr_text)
            if med_info["is_medication"] and med_info["spoken_summary"]:
                return med_info["spoken_summary"]
            elif ocr_text:
                return f"Text on container says: {ocr_text}"
            else:
                return "Hold the medicine bottle steady in front of the camera with the label facing forward."

        # ── 5. Banknote / Currency Reader ───────────────────────────────────
        if any(trigger in q for trigger in ["money", "bill", "cash", "rupee", "dollar", "currency", "note"]):
            currency_info = self.skills.identify_currency(ocr_text)
            if currency_info["is_currency"]:
                return f"This is a {currency_info['announcement']}."
            else:
                return "Hold the banknote flat and fully visible in front of the camera."

        # ── 6. Free-Space Walking Corridor Navigation ───────────────────────
        if any(trigger in q for trigger in ["which way", "where can i walk", "is it clear", "path clear", "corridor"]):
            corridor = self.pathfinder.find_navigable_corridor(current_frame.shape, current_detections)
            return corridor["spoken_guidance"]

        # ── 7. Social Dynamics Query ────────────────────────────────────────
        if any(trigger in q for trigger in ["waving", "handshake", "looking at me", "people", "smile"]):
            social_cue = self.skills.analyze_social_cues(current_detections)
            if social_cue:
                return social_cue
            return "No one appears to be interacting with you right now."

        # ── 8. Visual Question Answering via Local VLM / Cloud ──────────────
        if vlm_engine:
            try:
                answer = await vlm_engine.answer_question(current_frame, query)
                if answer:
                    return answer
            except Exception as e:
                logger.error(f"VLM question failed: {e}")

        return "I see the scene, but I'm not sure how to answer that specific question yet."
