"""
Spatial audio module for VisionAid smart glasses.
Generates direction-aware tones for alerts.
"""

import logging
import numpy as np
try:
    import sounddevice as sd
except ImportError:
    sd = None

logger = logging.getLogger(__name__)

class SpatialAudio:
    """Handles spatial audio cues."""

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize spatial audio.
        
        Args:
            sample_rate (int): Audio sample rate in Hz.
        """
        self.sample_rate = sample_rate
        if sd is None:
            logger.warning("sounddevice module not found. Spatial audio disabled.")

    def play_alert(self, direction: str, urgency: str):
        """
        Play a spatial alert sound.
        
        Args:
            direction (str): 'left', 'center', or 'right'.
            urgency (str): 'low', 'medium', or 'high'.
        """
        if sd is None:
            logger.error("Cannot play alert: sounddevice not available.")
            return

        logger.info(f"Playing spatial alert: direction={direction}, urgency={urgency}")
        
        duration = 0.2 if urgency == 'high' else 0.4
        freq = 880.0 if urgency == 'high' else (440.0 if urgency == 'medium' else 220.0)
        
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        tone = np.sin(2 * np.pi * freq * t)
        
        # Apply envelope to avoid clicking
        envelope = np.ones_like(tone)
        fade_samples = int(0.05 * self.sample_rate)
        if len(envelope) > 2 * fade_samples:
             envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
             envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
        tone = tone * envelope
        
        # Pan
        left_vol = 1.0
        right_vol = 1.0
        if direction == 'left':
            right_vol = 0.2
        elif direction == 'right':
            left_vol = 0.2
            
        stereo_tone = np.column_stack((tone * left_vol, tone * right_vol))
        
        try:
            sd.play(stereo_tone, samplerate=self.sample_rate)
            # sd.wait() # Uncomment to block until done, but usually we want async
        except Exception as e:
            logger.error(f"Error playing spatial audio: {e}")
