import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List, Tuple, Dict
import numpy as np
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

try:
    import torch
    from transformers import pipeline
    from PIL import Image
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    logger.warning("transformers or torch not installed. Depth estimation will be unavailable.")

@dataclass
class DepthResult:
    """Structured output for depth estimation."""
    depth_map: np.ndarray  # HxW float32 normalized 0-1, 0=far 1=near
    center_depth: float    # average depth in center region
    zones: Dict[str, float]  # left/center/right average depths
    hazard_detected: bool  # sudden depth change = stairs/curb
    closest_region: str    # 'left'/'center'/'right'

    def get(self, key: str, default=None):
        return getattr(self, key, default)


class DepthEstimator:
    """Monocular depth estimation using Depth Anything v2.

    Estimates relative depth from a single camera image — no stereo camera
    or LiDAR needed. This gives the glasses spatial awareness of how far
    objects are, which is critical for navigation and obstacle avoidance.

    The depth map is relative (not absolute metric depth), but we can:
    1. Estimate relative proximity (near/medium/far)
    2. Detect depth discontinuities (stairs, curbs, drop-offs)
    3. Combine with YOLO detections for object-specific distance estimates
    """

    @classmethod
    def is_available(cls) -> bool:
        """Checks if the required ML libraries are installed."""
        return HAS_TRANSFORMERS and torch.is_available()

    def __init__(self, model_name: str = 'depth-anything/Depth-Anything-V2-Small-hf', device: str = 'cpu'):
        """Initializes the depth estimator pipeline.
        
        Args:
            model_name: HuggingFace model identifier.
            device: 'cpu' or 'auto'. Auto detects CUDA/MPS.
        """
        self.model_name = model_name
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.pipe = None

        if not HAS_TRANSFORMERS:
            logger.error("Cannot initialize DepthEstimator: missing dependencies.")
            return

        # Auto-detect best device
        if device == 'auto' or device == 'cpu':
            if torch.cuda.is_available():
                self.device_id = 0  # 0 is the first CUDA device in HF pipelines
                self.device_name = 'cuda'
            elif torch.backends.mps.is_available():
                self.device_id = "mps"
                self.device_name = 'mps'
            else:
                self.device_id = -1
                self.device_name = 'cpu'
            if device == 'cpu' and self.device_name != 'cpu':
                self.device_id = -1
                self.device_name = 'cpu'
        else:
            self.device_id = -1 if device == 'cpu' else 0
            self.device_name = device

        logger.info(f"Initializing DepthEstimator with {model_name} on {self.device_name}")
        try:
            self.pipe = pipeline('depth-estimation', model=self.model_name, device=self.device_id)
            logger.info("DepthEstimator pipeline loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load DepthEstimator model: {e}")
            self.pipe = None

    def _process_frame_sync(self, frame: np.ndarray) -> DepthResult:
        """Synchronously runs inference and processes the depth map."""
        if self.pipe is None:
            # Return dummy data if unavailable
            return DepthResult(np.zeros((10,10), dtype=np.float32), 0.0, {'left':0,'center':0,'right':0}, False, 'center')

        start_time = time.perf_counter()
        
        try:
            # Convert numpy BGR to PIL Image RGB
            # Assuming frame is typical BGR from OpenCV
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                img_rgb = frame[:, :, ::-1]
            else:
                img_rgb = frame
            pil_image = Image.fromarray(img_rgb)
            
            # Run pipeline
            # The pipeline returns a dict with 'predicted_depth' (tensor) and 'depth' (PIL image)
            result = self.pipe(pil_image)
            
            # Process depth map
            # We want depth_map to be HxW float32 normalized 0-1, 1=near, 0=far
            # pipeline depth map PIL image is grayscale where 255=near, 0=far
            depth_img = result["depth"]
            depth_map = np.array(depth_img, dtype=np.float32) / 255.0
            
            h, w = depth_map.shape
            
            # Calculate zones
            third_w = w // 3
            left_zone = depth_map[:, :third_w]
            center_zone = depth_map[:, third_w:2*third_w]
            right_zone = depth_map[:, 2*third_w:]
            
            zones = {
                'left': float(np.mean(left_zone)),
                'center': float(np.mean(center_zone)),
                'right': float(np.mean(right_zone))
            }
            
            center_depth = zones['center']
            closest_region = max(zones, key=zones.get)
            
            # Hazard detection: check for sudden depth changes in the bottom half (where the ground is)
            bottom_half = depth_map[h//2:, :]
            # Simple gradient check along Y axis
            y_gradients = np.abs(np.diff(bottom_half, axis=0))
            max_gradient = np.max(y_gradients)
            # Threshold for sudden depth change (tunable parameter)
            hazard_detected = bool(max_gradient > 0.3) 

            depth_result = DepthResult(
                depth_map=depth_map,
                center_depth=center_depth,
                zones=zones,
                hazard_detected=hazard_detected,
                closest_region=closest_region
            )

        except Exception as e:
            logger.error(f"Error during depth estimation: {e}")
            # Fallback on error
            depth_result = DepthResult(np.zeros((10,10), dtype=np.float32), 0.0, {'left':0,'center':0,'right':0}, False, 'center')

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Depth estimation took {elapsed_ms:.2f}ms")
        
        return depth_result

    async def estimate_depth(self, frame: np.ndarray) -> DepthResult:
        """Asynchronously estimates depth for a given frame."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._process_frame_sync, frame)

    async def estimate(self, frame: np.ndarray) -> DepthResult:
        """Alias for estimate_depth."""
        return await self.estimate_depth(frame)

    def get_object_depth(self, depth_map: np.ndarray, bbox: Tuple[int, int, int, int]) -> str:
        """Given a YOLO bbox, estimate if that object is 'near', 'medium', or 'far'."""
        x1, y1, x2, y2 = bbox
        
        # Clamp to bounds
        h, w = depth_map.shape
        x1, x2 = max(0, x1), min(w, x2)
        y1, y2 = max(0, y1), min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return "unknown"
            
        obj_depth_map = depth_map[y1:y2, x1:x2]
        avg_depth = np.mean(obj_depth_map)
        
        # Thresholds: near > 0.7 normalized, medium 0.3-0.7, far < 0.3
        # Remember: 1.0 is near, 0.0 is far
        if avg_depth > 0.7:
            return "near"
        elif avg_depth >= 0.3:
            return "medium"
        else:
            return "far"

    def detect_drop_offs(self, depth_map: np.ndarray) -> List[str]:
        """Detects sudden depth changes that indicate stairs, curbs, or edges."""
        warnings = []
        h, w = depth_map.shape
        
        # Focus on the lower third of the image where ground drop-offs occur
        lower_third = depth_map[int(h*0.66):, :]
        
        # Split into left/center/right to give directional warnings
        third_w = w // 3
        regions = {
            'left': lower_third[:, :third_w],
            'ahead': lower_third[:, third_w:2*third_w],
            'right': lower_third[:, 2*third_w:]
        }
        
        for name, region in regions.items():
            # A sudden drop in value means it gets further away suddenly
            # Look for large negative gradients from top to bottom (y axis)
            y_diff = np.diff(region, axis=0)
            
            # If there's a strong negative change (current row - previous row is very negative)
            # It means the ground suddenly dropped away
            if np.min(y_diff) < -0.25: 
                if name == 'ahead':
                    warnings.append('Possible stairs or drop-off ahead')
                else:
                    warnings.append(f'Drop-off on your {name}')
                    
        return warnings
