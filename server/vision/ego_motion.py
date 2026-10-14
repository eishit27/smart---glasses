"""
VisionAid Ego-Motion Subtraction & Head-Rotation Compensator
===========================================================

Solves the primary flaw of wearable cameras:
When a blind user turns their head, stationary walls and benches appear to move
rapidly across the camera frame, triggering false collision alarms.

Methodology:
1. Sparse Optical Flow (Lucas-Kanade) on static background feature points.
2. RANSAC Affine Transformation / Homography estimation to calculate camera ego-motion (dx_head, dy_head).
3. Optional IMU Gyroscope Fusion: Angular rates (gyro_x, gyro_y) from temple-mounted MPU-6050.
4. Ego-Motion Subtraction: True Object Velocity = Apparent Image Velocity - Head Rotation Velocity.
"""

import cv2
import numpy as np
from typing import Tuple, List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class EgoMotionCompensator:
    def __init__(self, max_features: int = 150):
        self.max_features = max_features
        self.prev_gray: Optional[np.ndarray] = None
        self.prev_pts: Optional[np.ndarray] = None
        
        # Lucas-Kanade optical flow parameters
        self.lk_params = dict(
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
        )
        self.feature_params = dict(
            maxCorners=max_features,
            qualityLevel=0.01,
            minDistance=15,
            blockSize=7
        )

    def estimate_head_rotation(
        self,
        frame: np.ndarray,
        imu_angular_rates: Optional[Tuple[float, float, float]] = None
    ) -> Tuple[float, float]:
        """
        Estimates the camera's ego-motion (dx_pixels, dy_pixels) between frames.
        Returns (dx_ego, dy_ego).
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        if self.prev_gray is None:
            self.prev_gray = gray
            self.prev_pts = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
            return (0.0, 0.0)

        dx_ego, dy_ego = 0.0, 0.0

        # If physical IMU gyroscope data is available, prioritize it (zero latency)
        if imu_angular_rates is not None:
            # imu_angular_rates = (pitch_rate, yaw_rate, roll_rate) in deg/s
            # Approximate pixel translation assuming ~60 deg horizontal FOV across frame width
            h, w = gray.shape[:2]
            focal_pixels = w / (2.0 * np.tan(np.radians(30.0)))
            dt = 0.05  # ~20 FPS interval
            dx_ego = -np.radians(imu_angular_rates[1]) * focal_pixels * dt
            dy_ego = np.radians(imu_angular_rates[0]) * focal_pixels * dt
            self.prev_gray = gray
            return (dx_ego, dy_ego)

        # Visual Optical Flow Ego-Motion Estimation
        if self.prev_pts is not None and len(self.prev_pts) > 10:
            next_pts, status, err = cv2.calcOpticalFlowPyrLK(
                self.prev_gray, gray, self.prev_pts, None, **self.lk_params
            )

            if next_pts is not None and status is not None:
                good_prev = self.prev_pts[status == 1]
                good_next = next_pts[status == 1]

                if len(good_prev) >= 8:
                    # Estimate rigid affine transformation (translation + rotation) using RANSAC
                    matrix, inliers = cv2.estimateAffinePartial2D(good_prev, good_next)
                    if matrix is not None:
                        dx_ego = matrix[0, 2]
                        dy_ego = matrix[1, 2]

        # Refresh tracking points periodically
        self.prev_gray = gray
        self.prev_pts = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
        return (dx_ego, dy_ego)

    def compensate_object_velocities(
        self,
        apparent_velocities: List[Tuple[float, float]],
        dx_ego: float,
        dy_ego: float
    ) -> List[Tuple[float, float]]:
        """
        Subtracts head rotation from apparent object motions.
        True_v = Apparent_v - Ego_motion
        """
        compensated = []
        for vx_app, vy_app in apparent_velocities:
            true_vx = vx_app - dx_ego
            true_vy = vy_app - dy_ego
            compensated.append((true_vx, true_vy))
        return compensated
