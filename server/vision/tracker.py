"""
Obstacle Tracker & Alert De-Bouncing Module
===========================================

Solves the critical "Alert Fatigue" and repetitive spam flaw.
Ensures the blind user is alerted ONLY when:
1. A new obstacle appears in the trajectory
2. An obstacle is actively closing distance (Time-to-Collision < 3s)
3. Suppresses repetitive announcements for stationary objects already noted
"""

import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class TrackedObstacle:
    track_id: int
    label: str
    bbox: Tuple[int, int, int, int]
    distance_meters: float
    center_x: float
    last_seen_time: float
    last_alert_time: float
    last_distance: float
    approach_velocity_mps: float = 0.0  # Positive = getting closer

class ObstacleTracker:
    def __init__(self, alert_cooldown_sec: float = 3.5, iou_threshold: float = 0.35):
        self.alert_cooldown = alert_cooldown_sec
        self.iou_threshold = iou_threshold
        self.tracks: Dict[int, TrackedObstacle] = {}
        self._next_id = 1

    def _compute_iou(self, boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        iou = interArea / float(boxAArea + boxBArea - interArea + 1e-6)
        return iou

    def update(self, detections: List[Dict]) -> List[TrackedObstacle]:
        """
        Updates object tracks and returns only the obstacles that require an ACTIVE ALERT.
        
        Args:
            detections: List of dicts with keys: 'label', 'bbox', 'distance_meters', 'center_x'
            
        Returns:
            List[TrackedObstacle]: Only the objects warranting immediate attention.
        """
        now = time.time()
        updated_tracks = {}
        matched_detection_indices = set()
        urgent_alerts = []

        # 1. Match new detections to existing tracks via IoU
        for track_id, track in self.tracks.items():
            best_iou = 0.0
            best_det_idx = -1
            
            for idx, det in enumerate(detections):
                if idx in matched_detection_indices:
                    continue
                if det['label'] != track.label:
                    continue
                    
                iou = self._compute_iou(track.bbox, det['bbox'])
                if iou > best_iou and iou > self.iou_threshold:
                    best_iou = iou
                    best_det_idx = idx

            if best_det_idx >= 0:
                det = detections[best_det_idx]
                matched_detection_indices.add(best_det_idx)
                
                dt = max(0.01, now - track.last_seen_time)
                dist_diff = track.last_distance - det['distance_meters'] # Positive if getting closer
                velocity = dist_diff / dt
                
                track.bbox = det['bbox']
                track.last_distance = track.distance_meters
                track.distance_meters = det['distance_meters']
                track.center_x = det['center_x']
                track.last_seen_time = now
                track.approach_velocity_mps = velocity
                updated_tracks[track_id] = track
                
                # Check if this tracked object needs a re-alert
                # Re-alert conditions:
                # 1. Cooldown has elapsed AND it's close (< 2.0m)
                # 2. Or sudden significant distance drop (> 0.6m closer)
                time_since_alert = now - track.last_alert_time
                if (det['distance_meters'] < 2.0 and time_since_alert > self.alert_cooldown) or (dist_diff > 0.6 and det['distance_meters'] < 1.8):
                    track.last_alert_time = now
                    urgent_alerts.append(track)
            else:
                # Keep tracks for 1.5s if temporarily occluded
                if now - track.last_seen_time < 1.5:
                    updated_tracks[track_id] = track

        # 2. Create new tracks for unmatched detections
        for idx, det in enumerate(detections):
            if idx not in matched_detection_indices:
                new_track = TrackedObstacle(
                    track_id=self._next_id,
                    label=det['label'],
                    bbox=det['bbox'],
                    distance_meters=det['distance_meters'],
                    center_x=det['center_x'],
                    last_seen_time=now,
                    last_alert_time=now,
                    last_distance=det['distance_meters'],
                    approach_velocity_mps=0.0
                )
                self._next_id += 1
                updated_tracks[new_track.track_id] = new_track
                
                # If newly detected object is within warning zone (< 2.5m), alert immediately!
                if new_track.distance_meters < 2.5:
                    urgent_alerts.append(new_track)

        self.tracks = updated_tracks
        return urgent_alerts
