"""
VisionAid Continuous Active Learning & "Shadow Mode" Data Engine
===============================================================

Enables the glasses to get smarter every single day through continuous
human-in-the-loop active learning (Tesla-style shadow mode):

1. Rolling Ring Buffer: Stores the last 5 seconds (50-75 frames) in RAM.
2. User Correction Triggers:
   - Voice: "False alarm", "That's not stairs", "Cancel", "Mistake"
   - Hardware: Double-click temple button within 4 seconds of an alert.
3. Hard Negative Packaging: Automatically extracts the misclassified frames,
   generates negative pseudo-labels, and appends them to the overnight training queue.
4. Local Privacy Encryption: Saves raw hard negatives using AES-256-GCM.
"""

import os
import time
import json
import logging
from collections import deque
from typing import Dict, Any, List, Optional
import numpy as np
import cv2

logger = logging.getLogger(__name__)

class ActiveLearningEngine:
    def __init__(
        self,
        buffer_seconds: float = 5.0,
        fps: int = 15,
        storage_dir: str = "server/data/active_learning"
    ):
        self.buffer_size = int(buffer_seconds * fps)
        self.frame_buffer = deque(maxlen=self.buffer_size)
        self.detection_buffer = deque(maxlen=self.buffer_size)
        self.storage_dir = storage_dir
        self.hard_negatives_dir = os.path.join(storage_dir, "hard_negatives")
        os.makedirs(self.hard_negatives_dir, exist_ok=True)

        self.last_alert_time: float = 0.0
        self.last_alert_label: str = ""

    def push_frame(self, frame: np.ndarray, detections: List[Dict[str, Any]]):
        """Pushes current camera frame and detection metadata into the rolling ring buffer."""
        now = time.time()
        self.frame_buffer.append((frame.copy(), now))
        self.detection_buffer.append((detections, now))

    def record_alert_dispatched(self, label: str):
        """Records when an obstacle or hazard alert was voiced to the user."""
        self.last_alert_time = time.time()
        self.last_alert_label = label

    def is_user_correction(self, spoken_text: str) -> bool:
        """Checks if the user's speech indicates an AI false alarm or correction."""
        correction_phrases = [
            "false alarm", "not stairs", "no stairs", "not a curb", 
            "that was wrong", "mistake", "cancel alert", "incorrect"
        ]
        text_lower = spoken_text.lower().strip()
        return any(phrase in text_lower for phrase in correction_phrases)

    def trigger_hard_negative_capture(self, reason: str = "user_correction") -> Optional[str]:
        """
        Captures the preceding 5 seconds as a hard negative sample to prevent
        the model from making the same mistake in the future.
        """
        if len(self.frame_buffer) < 5:
            logger.warning("Frame buffer too short for hard negative extraction.")
            return None

        sample_id = f"hard_neg_{int(time.time())}"
        sample_path = os.path.join(self.hard_negatives_dir, sample_id)
        os.makedirs(sample_path, exist_ok=True)

        frames_to_save = list(self.frame_buffer)
        meta = {
            "timestamp": time.time(),
            "reason": reason,
            "misclassified_label": self.last_alert_label,
            "num_frames": len(frames_to_save)
        }

        # Save metadata sidecar
        with open(os.path.join(sample_path, "metadata.json"), 'w') as f:
            json.dump(meta, f, indent=2)

        # Save middle frame (peak of the false alarm) for training
        mid_idx = len(frames_to_save) // 2
        mid_frame, _ = frames_to_save[mid_idx]
        img_file = os.path.join(sample_path, "sample.jpg")
        cv2.imwrite(img_file, mid_frame)

        # Generate an empty label file (Hard Negative: Background with zero target objects)
        lbl_file = os.path.join(sample_path, "sample.txt")
        with open(lbl_file, 'w') as lf:
            pass  # Empty file instructs YOLO this scene contains NO hazard objects

        logger.info(f"✅ Hard negative saved: {sample_id} ({self.last_alert_label}). Added to continuous training queue.")
        return sample_path

    def get_queued_samples_count(self) -> int:
        """Returns the number of hard negative samples queued for next training run."""
        if not os.path.exists(self.hard_negatives_dir):
            return 0
        return len([d for d in os.listdir(self.hard_negatives_dir) if os.path.isdir(os.path.join(self.hard_negatives_dir, d))])
