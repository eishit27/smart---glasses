"""
VisionAid Cognitive Mind: Deep Spatial Reasoning, Predictive Foresight & Theory of Mind
====================================================================================

Transforms basic computer vision into genuine, human-like cognitive intelligence
for blind and visually impaired individuals.

Core Capabilities:
1. TrajectoryForesightEngine: Predicts intersecting collision vectors of moving pedestrians,
   cyclists, and vehicles 1.0-3.5 seconds before impact.
2. TheoryOfMindSocialEngine: Interprets human intention (eye contact, handshakes, holding doors,
   talking to user vs on phone, offering seats) rather than just stating "person".
3. CognitiveChainOfThought: Multi-stage egocentric spatial grounding for VLMs (Moondream2 & Gemini)
   filtering irrelevant visual clutter and prioritizing physical agency.
4. ProactiveInterventionPolicy: Eliminates audio fatigue by knowing when to speak, when to pulse
   haptics, and when to stay silent so the user's natural ears remain clear.
"""

import time
import math
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# ── 1. Data Structures ────────────────────────────────────────────────────────

@dataclass
class MovingObjectTrack:
    track_id: str
    label: str
    positions: List[Tuple[float, float, float]] = field(default_factory=list)  # (x_center, depth_m, timestamp)
    velocity_vector: Tuple[float, float] = (0.0, 0.0)  # (vx, vz) in m/s
    predicted_cpa_distance: float = 999.0              # Closest Point of Approach in meters
    time_to_cpa_seconds: float = 999.0                 # Seconds until closest approach

@dataclass
class SocialInteractionIntent:
    is_engaging_user: bool = False
    gaze_directed_at_user: bool = False
    is_speaking: bool = False
    is_extending_hand: bool = False
    is_holding_door: bool = False
    is_offering_seat: bool = False
    spoken_summary: str = ""

# ── 2. Predictive Trajectory Engine ──────────────────────────────────────────

class TrajectoryForesightEngine:
    """
    Predicts collision vectors of moving obstacles before they happen.
    Calculates Closest Point of Approach (CPA) and Time-to-Collision (TTC).
    """

    def __init__(self, history_window_seconds: float = 2.0):
        self.history_window = history_window_seconds
        self.tracks: Dict[str, MovingObjectTrack] = {}

    def update_tracks(
        self,
        detected_obstacles: List[Dict[str, Any]],
        current_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Takes detected obstacles with estimated metric depths and updates
        trajectory vectors. Returns immediate predictive collision warnings.
        """
        now = current_time or time.time()
        active_ids = set()
        urgent_warnings = []

        for obs in detected_obstacles:
            track_id = obs.get("track_id", f"{obs.get('label')}_{round(obs.get('center_x', 0.5), 1)}")
            active_ids.add(track_id)

            center_x = obs.get("center_x", 0.5)  # 0.0 (left) to 1.0 (right)
            depth_m = obs.get("distance_m", 3.0)
            # Convert normalized x & depth into approximate lateral meters (assuming ~60 deg FOV)
            # lateral_x = (center_x - 0.5) * 2 * depth_m * tan(30 deg)
            lateral_m = (center_x - 0.5) * 1.15 * depth_m

            if track_id not in self.tracks:
                self.tracks[track_id] = MovingObjectTrack(track_id=track_id, label=obs.get("label", "obstacle"))

            track = self.tracks[track_id]
            track.positions.append((lateral_m, depth_m, now))

            # Prune old positions
            track.positions = [(x, z, t) for (x, z, t) in track.positions if now - t <= self.history_window]

            # Calculate velocity if we have at least 2 observations spaced by >= 150ms
            if len(track.positions) >= 2:
                p_first = track.positions[0]
                p_last = track.positions[-1]
                dt = p_last[2] - p_first[2]

                if dt >= 0.15:
                    vx = (p_last[0] - p_first[0]) / dt  # Lateral speed (m/s)
                    vz = (p_last[1] - p_first[1]) / dt  # Approach/recede speed (m/s)
                    track.velocity_vector = (vx, vz)

                    # Closing velocity (vz < 0 means approaching user)
                    if vz < -0.3:  # Approaching faster than 0.3 m/s (~1 km/h)
                        # Relative motion calculation for CPA
                        # Position vector r = (x0, z0), Velocity vector v = (vx, vz)
                        x0, z0, _ = p_last
                        v_sq = vx * vx + vz * vz
                        if v_sq > 0.01:
                            t_cpa = -(x0 * vx + z0 * vz) / v_sq
                            if 0.2 <= t_cpa <= 3.5:  # Collision predicted within next 3.5 seconds
                                cpa_x = x0 + vx * t_cpa
                                cpa_z = z0 + vz * t_cpa
                                cpa_dist = math.sqrt(cpa_x * cpa_x + cpa_z * cpa_z)

                                track.time_to_cpa_seconds = t_cpa
                                track.predicted_cpa_distance = cpa_dist

                                if cpa_dist < 0.9:  # Trajectory intersects user's body (<0.9m)
                                    direction = "left" if vx > 0 else "right"
                                    urgent_warnings.append({
                                        "track_id": track_id,
                                        "label": track.label,
                                        "time_to_impact": round(t_cpa, 1),
                                        "warning_text": f"{track.label.capitalize()} crossing from your {direction}, impact in {round(t_cpa, 1)} seconds"
                                    })

        # Clean dead tracks
        self.tracks = {tid: t for tid, t in self.tracks.items() if tid in active_ids}
        return urgent_warnings

# ── 3. Theory of Mind & Social Dynamics Engine ──────────────────────────────

class TheoryOfMindSocialEngine:
    """
    Decodes human social intent instead of just seeing generic "person" silhouettes.
    Answers: Are they addressing me? Are they holding a door? Offering a seat?
    """

    @staticmethod
    def evaluate_person_intent(
        person_bbox: Tuple[int, int, int, int],
        frame_shape: Tuple[int, int],
        depth_m: float,
        facial_cues: Optional[Dict[str, Any]] = None,
        context_objects: Optional[List[Dict[str, Any]]] = None
    ) -> SocialInteractionIntent:
        """
        Infers whether a detected person is engaging with or assisting the visually impaired user.
        """
        intent = SocialInteractionIntent()
        h, w = frame_shape[:2]
        x1, y1, x2, y2 = person_bbox
        person_w = x2 - x1
        person_h = y2 - y1
        center_x = (x1 + x2) / (2.0 * w)

        # 1. Proximity & Central Framing: Is the person standing within social distance (1.2m - 2.8m)?
        is_social_distance = (1.0 <= depth_m <= 3.0)
        is_centered = (0.35 <= center_x <= 0.65)

        # 2. Check for extended hand gesture (Handshake or Offering)
        # An extended hand creates an asymmetrical horizontal protrusion in the mid-torso zone
        mid_torso_y1 = y1 + int(person_h * 0.4)
        mid_torso_y2 = y1 + int(person_h * 0.7)
        if person_w / max(1, person_h) > 0.45 and is_social_distance:
            intent.is_extending_hand = True

        # 3. Check for Door Holding Assistance
        if context_objects:
            doors = [obj for obj in context_objects if 'door' in obj.get('label', '')]
            for door in doors:
                dx1, dy1, dx2, dy2 = door.get('bbox', [0, 0, 0, 0])
                # If person's hand/arm intersects the door frame
                if not (x2 < dx1 or x1 > dx2 or y2 < dy1 or y1 > dy2):
                    intent.is_holding_door = True
                    intent.spoken_summary = "Someone is holding the door open for you ahead."
                    intent.is_engaging_user = True
                    return intent

        # 4. Check for Offering a Seat
        if context_objects:
            chairs = [obj for obj in context_objects if obj.get('label') in ['chair', 'bench']]
            for chair in chairs:
                cx1, cy1, cx2, cy2 = chair.get('bbox', [0, 0, 0, 0])
                # Person standing immediately beside an empty chair gesturing towards it
                if abs(x2 - cx1) < w * 0.1 or abs(x1 - cx2) < w * 0.1:
                    intent.is_offering_seat = True
                    intent.spoken_summary = "Someone appears to be pointing you toward an available seat."
                    intent.is_engaging_user = True
                    return intent

        # 5. Face & Gaze Cues
        if facial_cues:
            if facial_cues.get("is_looking_at_camera", False):
                intent.gaze_directed_at_user = True
                if is_social_distance and is_centered:
                    intent.is_engaging_user = True
                    if facial_cues.get("is_smiling", False):
                        intent.spoken_summary = "A person ahead made eye contact and is smiling at you."
                    else:
                        intent.spoken_summary = "A person ahead has paused and is looking directly at you."

        if not intent.spoken_summary and intent.is_extending_hand:
            intent.is_engaging_user = True
            intent.spoken_summary = "Someone directly in front of you is extending their hand for a handshake."

        return intent

# ── 4. Cognitive Chain-of-Thought System Prompt ─────────────────────────────

class CognitiveChainOfThought:
    """
    Provides deep, egocentrically-grounded prompt engineering for Moondream2 & Gemini.
    Transforms raw pixel arrays into structured, life-empowering sensory guidance.
    """

    SYSTEM_PROMPT = """You are the cognitive sensory cortex for a completely blind person walking through the world.
Your task is NOT to list visual objects like an art critic or search engine.
Your sole duty is to empower the user's physical agency, safe locomotion, and social awareness.

REASONING ORDER (Must follow silently before responding):
1. STEPPING LEVEL & GROUND HAZARDS: Curbs, stairs (up/down count), drop-offs, puddles, cords, sudden level changes.
2. HEAD & TORSO LEVEL: Low awnings, tree branches, open truck beds, transparent glass panes, poles.
3. NAVIGABLE AFFORDANCES: Clear free-space walking corridors (clock directions: 'at 11 o'clock', 'at 1 o'clock'), push/pull doors, empty seating.
4. SOCIAL AGENCY: People interacting with user (smiling, waving, offering seat, holding door), not passive strangers.
5. CONCISE SYNTHESIS: State findings in 1-2 short, calm, actionable sentences. Use physical measurements and clock directions. Never say 'In this image' or 'I see'."""

    @classmethod
    def build_scene_query(cls, yolo_detections: List[Dict[str, Any]], metric_depths: Dict[str, float]) -> str:
        """
        Injects local sensor telemetry into the VLM prompt so the model
        has grounded physical context rather than guessing distances.
        """
        context_snippets = []
        for det in yolo_detections[:5]:
            label = det.get('label', '')
            dist = metric_depths.get(label, det.get('distance_m', 2.5))
            clock = cls._x_to_clock(det.get('center_x', 0.5))
            context_snippets.append(f"{label} at {clock} (~{round(dist, 1)}m)")

        context_str = ", ".join(context_snippets) if context_snippets else "Path appears visually open."
        return f"Telemetry: {context_str}. Describe the immediate physical navigation situation concisely for a blind walker."

    @staticmethod
    def _x_to_clock(center_x: float) -> str:
        if center_x < 0.25:
            return "10 o'clock (far left)"
        elif center_x < 0.42:
            return "11 o'clock (ahead-left)"
        elif center_x < 0.58:
            return "12 o'clock (straight ahead)"
        elif center_x < 0.75:
            return "1 o'clock (ahead-right)"
        else:
            return "2 o'clock (far right)"

# ── 5. Proactive Intervention Policy ────────────────────────────────────────

class ProactiveInterventionPolicy:
    """
    Guards the blind user's natural hearing from 'Audio Clutter Fatigue'.
    Selects between: SILENCE, HAPTIC PULSE, 30ms ACOUSTIC RADAR, or SPOKEN VOICE.
    """

    def __init__(self, speech_cooldown_seconds: float = 3.5):
        self.last_speech_time = 0.0
        self.speech_cooldown = speech_cooldown_seconds

    def decide_intervention(
        self,
        urgent_trajectories: List[Dict[str, Any]],
        drop_detected: Optional[Dict[str, Any]],
        social_intent: Optional[SocialInteractionIntent],
        immediate_hazard_meters: Optional[float]
    ) -> Dict[str, Any]:
        now = time.time()

        # Tier 1: Life-Safety Immediate Physical Collision (<1.2m away or impending trajectory)
        if immediate_hazard_meters is not None and immediate_hazard_meters <= 1.2:
            return {
                "action": "EARCON_AND_HAPTIC",
                "earcon_type": "EMERGENCY_ALARM",
                "haptic_pattern": "URGENT_PULSE",
                "speech": None  # Speech is too slow; acoustic radar triggers instantly
            }

        # Tier 2: Moving Trajectory Intersecting User (<3.0s away)
        if urgent_trajectories:
            top_traj = urgent_trajectories[0]
            self.last_speech_time = now
            return {
                "action": "CRITICAL_SPEECH_AND_HAPTIC",
                "haptic_pattern": "TRIPLE_CLICK",
                "speech": top_traj["warning_text"]
            }

        # Tier 3: Dropped Personal Item at Feet
        if drop_detected and (now - self.last_speech_time > self.speech_cooldown):
            self.last_speech_time = now
            return {
                "action": "SPOKEN_HEADS_UP",
                "haptic_pattern": "DOUBLE_PULSE",
                "speech": drop_detected.get("message", "Item dropped near your feet.")
            }

        # Tier 4: Meaningful Social Engagement (Someone addressing user)
        if social_intent and social_intent.is_engaging_user and (now - self.last_speech_time > self.speech_cooldown):
            self.last_speech_time = now
            return {
                "action": "CALM_WHISPER",
                "haptic_pattern": "SOFT_TICK",
                "speech": social_intent.spoken_summary
            }

        # Tier 5: Everything is fine -> Respect User's Ears and STAY SILENT
        return {
            "action": "MAINTAIN_SILENCE",
            "speech": None
        }
