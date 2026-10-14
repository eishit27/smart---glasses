import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    import torch
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    logger.warning("ultralytics or torch not installed. Object detection will be unavailable.")

@dataclass
class Detection:
    """Represents a single object detection."""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    center_x: float  # 0.0=left, 1.0=right for spatial audio
    area_ratio: float  # how much of frame the object takes up (proxy for proximity)


class ObjectDetector:
    """Local real-time object detection using YOLOv8.

    This module runs ENTIRELY on-device for zero-latency obstacle detection.
    Unlike the Gemini-based scene analyzer, this works offline and provides
    structured bounding boxes with class labels in ~20ms per frame.

    Used for:
    - Immediate obstacle alerts (doesn't wait for cloud API)
    - Providing structured object data to the navigation system
    - Offline fallback when internet is unavailable
    """

    IMPORTANT_CLASSES = {
        'stairs_up', 'stairs_down', 'curb', 'head_hazard', 'ground_obstacle',
        'pole_bollard', 'glass_door', 'crosswalk', 'pedestrian_signal',
        'person', 'car', 'bicycle', 'truck', 'bus', 'motorcycle', 
        'dog', 'cat', 'chair', 'table', 'door', 'stairs', 
        'traffic light', 'stop sign', 'fire hydrant', 'bench'
    }

    def __init__(self, model_name: str = 'yolo11n.pt', confidence_threshold: float = 0.35, device: str = 'cpu'):
        """Initializes the object detector with SOTA YOLO11 (or YOLOv8 fallback).
        
        Prioritizes custom-trained accessibility hazard weights (server/models/hazard_yolo11.pt).
        """
        import os
        custom_weights = "server/models/hazard_yolo11.pt"
        if os.path.exists(custom_weights):
            self.model_name = custom_weights
            logger.info(f"🎯 Found custom accessibility-trained hazard weights: {custom_weights}")
        else:
            self.model_name = model_name

        self.confidence_threshold = confidence_threshold
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.model = None

        if not HAS_YOLO:
            logger.error("Cannot initialize ObjectDetector: missing dependencies.")
            return

        # Auto-detect best device if 'auto' or default
        if device == 'auto' or device == 'cpu':
            if torch.cuda.is_available():
                self.device = 'cuda'
            elif torch.backends.mps.is_available():
                self.device = 'mps'
            else:
                self.device = 'cpu'
            if device == 'cpu' and self.device != 'cpu':
                self.device = 'cpu'
        else:
            self.device = device

        logger.info(f"Initializing YOLO object detector with {self.model_name} on {self.device}")
        try:
            try:
                self.model = YOLO(self.model_name)
            except Exception as e:
                logger.warning(f"Could not load {self.model_name} ({e}), falling back to yolov8n.pt...")
                self.model = YOLO('yolov8n.pt')

            # Warmup
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model(dummy_frame, device=self.device, verbose=False)
            logger.info("YOLO detector initialized and warmed up successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.model = None

    def detect_sync(self, frame: np.ndarray) -> List[Detection]:
        """Synchronously detects objects in a frame.
        
        Args:
            frame: BGR numpy array image (e.g. from cv2)
            
        Returns:
            List of Detection objects.
        """
        if self.model is None:
            return []

        start_time = time.perf_counter()
        detections = []
        
        try:
            # Run inference
            results = self.model(frame, device=self.device, verbose=False)
            
            # Process results
            if results and len(results) > 0:
                result = results[0]
                frame_h, frame_w = frame.shape[:2]
                frame_area = frame_h * frame_w
                
                boxes = result.boxes
                for box in boxes:
                    conf = float(box.conf[0])
                    if conf < self.confidence_threshold:
                        continue
                        
                    cls_id = int(box.cls[0])
                    label = self.model.names[cls_id]
                    
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Calculate center_x (0.0 to 1.0)
                    center_x = ((x1 + x2) / 2) / frame_w
                    
                    # Calculate area ratio
                    box_area = (x2 - x1) * (y2 - y1)
                    area_ratio = box_area / frame_area
                    
                    detections.append(Detection(
                        label=label,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        center_x=center_x,
                        area_ratio=area_ratio
                    ))
        except Exception as e:
            logger.error(f"Error during object detection: {e}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Detection took {elapsed_ms:.2f}ms, found {len(detections)} objects")
        
        return detections

    async def detect(self, frame: np.ndarray) -> List[Detection]:
        """Asynchronously detects objects in a frame, not blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.detect_sync, frame)

    def get_spatial_description(self, detections: List[Detection], frame_width: int) -> str:
        """Converts detections to a natural language spatial description."""
        if not detections:
            return "Clear path ahead."
            
        descriptions = []
        # Sort by proximity (area ratio) descending
        sorted_dets = sorted(detections, key=lambda d: d.area_ratio, reverse=True)
        
        for det in sorted_dets:
            if det.label not in self.IMPORTANT_CLASSES and det.area_ratio < 0.1:
                continue # Skip small unimportant objects in summary
                
            position = "ahead"
            if det.center_x < 0.33:
                position = "on your left"
            elif det.center_x > 0.67:
                position = "on your right"
                
            descriptions.append(f"{det.label} {position}")
            
            # Limit to top 3 objects to avoid overwhelming the user
            if len(descriptions) >= 3:
                break
                
        if not descriptions:
            return "Clear path ahead."
            
        return ", ".join(descriptions)

    def get_priority_alerts(self, detections: List[Detection], frame_width: int) -> List[str]:
        """Returns HIGH priority alerts for dangerous or rapidly approaching objects."""
        alerts = []
        
        DANGER_CLASSES = {'person', 'car', 'bicycle', 'truck', 'bus', 'motorcycle', 'dog', 'fire hydrant', 'stop sign', 'traffic light'}
        DANGER_AREA_THRESHOLD = 0.15  # 15% of screen = dangerously close
        
        for det in detections:
            if det.label in DANGER_CLASSES and det.area_ratio > DANGER_AREA_THRESHOLD:
                direction = "Ahead"
                if det.center_x < 0.33:
                    direction = "Left"
                elif det.center_x > 0.67:
                    direction = "Right"
                    
                alerts.append(f"URGENT: {det.label} very close {direction.lower()}!")
                
        return alerts
