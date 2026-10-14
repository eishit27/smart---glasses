"""Hybrid Vision Pipeline — the brain that decides what to run and when.

This pipeline intelligently combines fast local models with the Gemini
cloud API to provide the best possible experience:

Fast Path (always runs, ~30ms):
    Frame → YOLO (objects) + Depth (distances) → Immediate alerts

Smart Path (runs on command or periodically):
    Frame → Gemini (rich scene understanding) → Detailed description

This dual-path approach means:
- Safety alerts are INSTANT (local inference)
- Descriptions are RICH (cloud AI)
- System works OFFLINE (graceful degradation)
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
import numpy as np
from dataclasses import dataclass, field

from .object_detector import ObjectDetector
from .open_vocabulary_detector import OpenVocabularyHazardDetector
from .depth_estimator import DepthEstimator
from .scene_analyzer import SceneAnalyzer
from .ocr_reader import OCRReader
from .face_recognizer import FaceRecognizer
from .navigation import NavigationAssistant
from .local_vlm import LocalVLM
from .sota_vlm import SOTAVisionLanguageEngine

logger = logging.getLogger(__name__)

@dataclass
class Detection:
    label: str
    confidence: float
    bbox: List[int]
    distance: Optional[float] = None

@dataclass
class FastScanResult:
    detections: List[Detection] = field(default_factory=list)
    depth_zones: Dict[str, float] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)
    spatial_description: str = ""
    hazards: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0

@dataclass
class NavigationResult:
    directions: str = ""
    obstacles: List[Detection] = field(default_factory=list)
    safety_status: str = "safe"

class HybridVisionPipeline:
    def __init__(self, config: Any):
        """Initialize all vision sub-modules based on the provided configuration."""
        self.config = config
        self.api_key = getattr(config, 'gemini_api_key', None)
        
        logger.info("Initializing HybridVisionPipeline modules...")
        
        # Always loaded local modules (SOTA Edge Models)
        self.object_detector = ObjectDetector()  # Prioritizes custom-trained hazard_yolo11.pt
        self.open_vocab_detector = OpenVocabularyHazardDetector()  # YOLO-World zero-shot open vocabulary
        self.depth_estimator = DepthEstimator()  # SOTA Depth Anything v2
        self.ocr_reader = OCRReader(api_key=self.api_key)
        self.face_recognizer = FaceRecognizer()
        
        # World-Class Multimodal Cognitive Brain (Qwen2.5-VL / Florence-2 / Moondream2)
        self.sota_vlm = SOTAVisionLanguageEngine()
        self.local_vlm = self.sota_vlm  # Backward compatibility alias
        
        # Cloud modules loaded if API key is available
        self.scene_analyzer = None
        self.navigation_assistant = None
        
        if self.api_key:
            self.scene_analyzer = SceneAnalyzer(api_key=self.api_key)
            self.navigation_assistant = NavigationAssistant(api_key=self.api_key)
        else:
            logger.info("Operating in standalone offline mode: SOTA VLM (Qwen2.5-VL / Florence-2) active.")
            
    @property
    def is_online(self) -> bool:
        """Returns True if the Gemini API key is available and online features are enabled."""
        return self.api_key is not None
        
    @property
    def capabilities(self) -> Dict[str, bool]:
        """Returns a dictionary of available capabilities."""
        return {
            "hazard_detection": True,
            "open_vocabulary_hazards": True,
            "depth_estimation": True,
            "face_recognition": True,
            "ocr": True,
            "local_sota_reasoning": True,
            "scene_understanding": self.is_online or True,
            "advanced_navigation": self.is_online or True
        }

    def _combine_yolo_depth(self, detections: List[Any], depth_map: np.ndarray, frame_width: int) -> List[Detection]:
        """Combine YOLO detections with depth estimates to evaluate distance."""
        enhanced = []
        for det in detections:
            if isinstance(det, dict):
                bbox = det.get('bbox', [0, 0, 0, 0])
                label = det.get('label', 'unknown')
                confidence = det.get('confidence', 0.0)
            else:
                bbox = getattr(det, 'bbox', [0, 0, 0, 0])
                label = getattr(det, 'label', 'unknown')
                confidence = getattr(det, 'confidence', 0.0)
            
            # Calculate center of bounding box to sample depth
            cx = int((bbox[0] + bbox[2]) / 2)
            cy = int((bbox[1] + bbox[3]) / 2)
            
            # Ensure coordinates are within depth map bounds
            h, w = depth_map.shape[:2]
            cx = max(0, min(cx, w - 1))
            cy = max(0, min(cy, h - 1))
            
            distance = float(depth_map[cy, cx]) if len(depth_map.shape) == 2 else 0.0
            
            enhanced.append(Detection(
                label=label,
                confidence=confidence,
                bbox=bbox,
                distance=distance
            ))
        return enhanced

    async def fast_scan(self, frame: np.ndarray) -> FastScanResult:
        """Runs YOLO + Depth in parallel (both local, fast) on every frame (~30ms)."""
        start_time = time.time()
        
        # Run YOLO and Depth in parallel
        detect_task = asyncio.create_task(self.object_detector.detect(frame))
        depth_task = asyncio.create_task(self.depth_estimator.estimate(frame))
        
        try:
            detections_raw, depth_result = await asyncio.gather(detect_task, depth_task)
            depth_map = depth_result.get('depth_map', np.zeros(frame.shape[:2]))
            depth_zones = depth_result.get('zones', {"left": 0.0, "center": 0.0, "right": 0.0})
        except Exception as e:
            logger.error(f"Error in fast_scan: {e}")
            detections_raw = []
            depth_map = np.zeros(frame.shape[:2])
            depth_zones = {"left": 0.0, "center": 0.0, "right": 0.0}

        detections = self._combine_yolo_depth(detections_raw, depth_map, frame.shape[1])
        
        alerts = []
        hazards = []
        spatial_desc_parts = []
        
        for det in detections:
            if det.distance is not None and det.distance < 1.0:
                alerts.append(f"Close {det.label} ahead!")
            pos = "left" if det.bbox[0] < frame.shape[1]/3 else ("right" if det.bbox[2] > 2*frame.shape[1]/3 else "center")
            dist_str = "near" if det.distance and det.distance < 2.0 else "far"
            spatial_desc_parts.append(f"{det.label} {dist_str} on {pos}")
            
        if depth_zones.get("center", 5.0) < 0.5:
            hazards.append("Immediate obstacle in center")

        processing_time_ms = (time.time() - start_time) * 1000

        return FastScanResult(
            detections=detections,
            depth_zones=depth_zones,
            alerts=alerts,
            spatial_description=", ".join(spatial_desc_parts),
            hazards=hazards,
            processing_time_ms=processing_time_ms
        )

    async def full_describe(self, frame: np.ndarray) -> str:
        """
        Generates a rich scene description.
        - Online: Uses Gemini 2.5 Flash enriched with YOLO detections.
        - Offline: Uses local SOTA VLM (Qwen2.5-VL / Florence-2 / Moondream2).
        - Fallback: Uses fast YOLO + Depth spatial summary.
        """
        # If online with Gemini available, use cloud AI
        if self.is_online and self.scene_analyzer:
            try:
                detections = await self.object_detector.detect(frame)
                det_labels = [getattr(d, 'label', d.get('label') if isinstance(d, dict) else 'object') for d in detections]
                context = f"Objects detected: {', '.join(det_labels)}" if det_labels else ""
                
                description = await self.scene_analyzer.analyze(frame, context=context)
                if description and not description.startswith("Error"):
                    return description
            except Exception as e:
                logger.warning(f"Cloud scene analysis failed ({e}). Falling back to local SOTA VLM...")

        # OFFLINE PATH: Local SOTA VLM (Qwen2.5-VL / Florence-2 / Moondream2)
        try:
            logger.info("Running local SOTA VLM for scene description...")
            vlm_caption = await self.sota_vlm.describe_scene(frame)
            if vlm_caption:
                return f"[Offline AI] {vlm_caption}"
        except Exception as e:
            logger.error(f"Local SOTA VLM description failed: {e}")

        # Final Fallback: Fast YOLO + Depth spatial description
        scan = await self.fast_scan(frame)
        return f"Offline spatial summary: {scan.spatial_description}"

    async def answer_question(self, frame: np.ndarray, question: str) -> str:
        """
        Answers a specific question about what the camera sees.
        Can run offline via SOTA VLM (Qwen2.5-VL / Florence-2) or online via Gemini.
        """
        try:
            return await self.sota_vlm.answer_question(frame, question)
        except Exception as e:
            logger.error(f"Visual Q&A failed: {e}")
            return "Could not determine an answer."

    async def read_text(self, frame: np.ndarray) -> Dict[str, Any]:
        """Delegates to OCRReader."""
        return await self.ocr_reader.read_text(frame)

    async def identify_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Delegates to FaceRecognizer."""
        # A complete implementation would match YOLO person boxes with FaceRecognizer boxes
        faces = await self.face_recognizer.recognize(frame)
        return faces

    async def navigate(self, frame: np.ndarray) -> NavigationResult:
        """Combines YOLO + Depth + Gemini navigation for robust situational awareness."""
        scan_result = await self.fast_scan(frame)
        
        directions = "Proceed with caution."
        safety_status = "safe"
        
        if scan_result.hazards or scan_result.alerts:
            safety_status = "unsafe"
            directions = "Stop. " + " ".join(scan_result.alerts + scan_result.hazards)
        elif self.is_online and self.navigation_assistant:
            try:
                # Ask navigation assistant using spatial description as context
                nav_instructions = await self.navigation_assistant.get_directions(frame, context=scan_result.spatial_description)
                directions = nav_instructions
            except Exception as e:
                logger.error(f"Cloud navigation failed: {e}")
                directions = f"Path is clear. {scan_result.spatial_description}"
        else:
            directions = f"Path seems clear. {scan_result.spatial_description}"
            
        return NavigationResult(
            directions=directions,
            obstacles=[d for d in scan_result.detections if d.distance and d.distance < 2.0],
            safety_status=safety_status
        )
