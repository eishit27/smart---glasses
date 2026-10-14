"""
Recording management module for VisionAid smart glasses.
Handles saving frames, recording videos, and managing storage quota.
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
import cv2

logger = logging.getLogger(__name__)

class Recorder:
    """Manages saving frames and video recordings."""

    def __init__(self, base_dir: str = "recordings", max_storage_gb: float = 5.0):
        """
        Initialize the recorder.
        
        Args:
            base_dir (str): Base directory for recordings.
            max_storage_gb (float): Maximum allowed storage usage in GB.
        """
        self.base_dir = base_dir
        self.max_storage_bytes = max_storage_gb * 1024 * 1024 * 1024
        self._is_recording = False
        self._video_writer = None
        self._video_path = None
        self._recording_fps = 10
        self._frame_size = None
        
        os.makedirs(self.base_dir, exist_ok=True)
        
    def _get_daily_dir(self) -> str:
        """Get or create the directory for the current date."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        daily_dir = os.path.join(self.base_dir, date_str)
        os.makedirs(daily_dir, exist_ok=True)
        return daily_dir

    def _check_quota(self):
        """Check if storage exceeds quota and log warning."""
        usage = self.get_storage_usage()
        if usage['total_bytes'] > self.max_storage_bytes:
            logger.warning(f"Storage quota exceeded: {usage['total_bytes'] / (1024**3):.2f} GB used out of {self.max_storage_bytes / (1024**3):.2f} GB")

    async def save_frame(self, frame: np.ndarray, metadata: Optional[Dict] = None, encrypt: bool = True) -> str:
        """
        Save a single frame with optional metadata.
        
        Args:
            frame (np.ndarray): The image frame.
            metadata (dict, optional): Metadata to save alongside the frame.
            encrypt (bool): If True, encrypts image and metadata with AES-256-GCM.
            
        Returns:
            str: Path to the saved file.
        """
        try:
            self._check_quota()
            daily_dir = self._get_daily_dir()
            timestamp = datetime.now().strftime("%H-%M-%S-%f")
            
            # Encode frame to JPEG
            success, buffer = cv2.imencode('.jpg', frame)
            if not success:
                raise ValueError("Failed to encode frame to JPEG")
            jpeg_bytes = buffer.tobytes()

            if encrypt:
                from security.crypto import SecurityManager
                sec_mgr = SecurityManager()
                
                # Encrypt JPEG bytes
                enc_image = sec_mgr.encrypt_data(jpeg_bytes)
                image_path = os.path.join(daily_dir, f"frame_{timestamp}.jpg.enc")
                
                def write_enc():
                    with open(image_path, "wb") as f:
                        f.write(enc_image)
                await asyncio.to_thread(write_enc)

                if metadata:
                    meta_bytes = json.dumps(metadata, indent=2).encode('utf-8')
                    enc_meta = sec_mgr.encrypt_data(meta_bytes)
                    meta_path = os.path.join(daily_dir, f"frame_{timestamp}.json.enc")
                    def write_meta():
                        with open(meta_path, "wb") as f:
                            f.write(enc_meta)
                    await asyncio.to_thread(write_meta)
            else:
                image_path = os.path.join(daily_dir, f"frame_{timestamp}.jpg")
                await asyncio.to_thread(cv2.imwrite, image_path, frame)
                if metadata:
                    meta_path = os.path.join(daily_dir, f"frame_{timestamp}.json")
                    with open(meta_path, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    
            logger.info(f"Saved secure frame to {image_path} (encrypted={encrypt})")
            return image_path
            
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
            raise

    async def start_recording(self, fps: int = 10, frame_size: tuple = (640, 480)) -> str:
        """
        Start recording a video clip.
        
        Args:
            fps (int): Frames per second.
            frame_size (tuple): Width and height of the frames.
            
        Returns:
            str: Path to the video file being recorded.
        """
        if self._is_recording:
            logger.warning("Already recording.")
            return self._video_path
            
        self._check_quota()
        daily_dir = self._get_daily_dir()
        timestamp = datetime.now().strftime("%H-%M-%S")
        self._video_path = os.path.join(daily_dir, f"video_{timestamp}.mp4")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._video_writer = cv2.VideoWriter(self._video_path, fourcc, fps, frame_size)
        
        self._is_recording = True
        self._recording_fps = fps
        self._frame_size = frame_size
        
        logger.info(f"Started recording video to {self._video_path}")
        return self._video_path

    async def add_frame_to_video(self, frame: np.ndarray):
        """Add a frame to the currently recording video."""
        if not self._is_recording or self._video_writer is None:
            logger.warning("Cannot add frame: Not currently recording.")
            return
            
        # Ensure size matches
        if (frame.shape[1], frame.shape[0]) != self._frame_size:
            frame = cv2.resize(frame, self._frame_size)
            
        self._video_writer.write(frame)

    async def stop_recording(self) -> Optional[str]:
        """
        Stop the current recording.
        
        Returns:
            str: Path to the saved video file, or None if not recording.
        """
        if not self._is_recording:
            return None
            
        self._is_recording = False
        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None
            
        path = self._video_path
        self._video_path = None
        logger.info(f"Stopped recording. Video saved to {path}")
        return path

    def list_recordings(self) -> List[Dict]:
        """
        List all stored recordings organized by date.
        
        Returns:
            list: List of dictionaries containing date, files, and sizes.
        """
        recordings = []
        if not os.path.exists(self.base_dir):
            return recordings
            
        for date_dir in os.listdir(self.base_dir):
            dir_path = os.path.join(self.base_dir, date_dir)
            if os.path.isdir(dir_path):
                files = os.listdir(dir_path)
                size = sum(os.path.getsize(os.path.join(dir_path, f)) for f in files)
                recordings.append({
                    "date": date_dir,
                    "file_count": len(files),
                    "size_bytes": size,
                    "path": dir_path
                })
        return sorted(recordings, key=lambda x: x['date'], reverse=True)

    def get_storage_usage(self) -> Dict:
        """
        Get current storage usage for recordings.
        
        Returns:
            dict: Total bytes used and maximum allowed bytes.
        """
        total_size = 0
        if os.path.exists(self.base_dir):
            for dirpath, _, filenames in os.walk(self.base_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
                        
        return {
            "total_bytes": total_size,
            "max_bytes": self.max_storage_bytes,
            "percentage": (total_size / self.max_storage_bytes) * 100 if self.max_storage_bytes > 0 else 0
        }
