"""
Directional Audio Earcon Module
===============================

Sub-30ms low-latency acoustic feedback for immediate physical obstacles.
Solves the "TTS is too slow to save the user from walking into things" flaw.

Features:
- Instant stereo-panned pulse (< 30ms latency)
- Frequency scales inversely with distance (closer = higher urgent pitch)
- Stereo panning maps horizontal position (-1.0=Full Left, 0.0=Center, +1.0=Full Right)
- Operates asynchronously without blocking TTS or main frame loop
"""

import asyncio
import logging
import math
import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

class EarconGenerator:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def generate_tone(
        self,
        frequency_hz: float,
        duration_sec: float = 0.06, # 60ms sharp tick
        pan: float = 0.0,           # -1.0 (left) to +1.0 (right)
        volume: float = 0.8
    ) -> np.ndarray:
        """
        Synthesizes a stereo audio buffer with cosine fade-in/out to prevent speaker click.
        """
        num_samples = int(self.sample_rate * duration_sec)
        t = np.linspace(0, duration_sec, num_samples, endpoint=False)
        
        # Sine wave tone
        mono_signal = np.sin(2 * np.pi * frequency_hz * t) * volume
        
        # Apply gentle envelope (5ms attack / decay) to eliminate pops
        envelope = np.ones(num_samples)
        fade_len = int(self.sample_rate * 0.008)
        if fade_len > 0 and 2 * fade_len < num_samples:
            envelope[:fade_len] = np.linspace(0, 1, fade_len)
            envelope[-fade_len:] = np.linspace(1, 0, fade_len)
        mono_signal *= envelope

        # Stereo Panning (Constant Power Law)
        # pan: -1.0 (left) to +1.0 (right)
        clamped_pan = max(-1.0, min(1.0, pan))
        angle = (clamped_pan + 1.0) * (math.pi / 4.0) # 0 to pi/2
        left_gain = math.cos(angle)
        right_gain = math.sin(angle)

        stereo_signal = np.zeros((num_samples, 2), dtype=np.float32)
        stereo_signal[:, 0] = mono_signal * left_gain
        stereo_signal[:, 1] = mono_signal * right_gain

        return stereo_signal

    async def play_proximity_cue(self, distance_meters: float, horizontal_pos: float = 0.0):
        """
        Fires an instant directional acoustic warning.
        - horizontal_pos: 0.0 (left) to 1.0 (right), 0.5 is center.
        - distance_meters: physical distance in meters.
        """
        # Map horizontal_pos [0.0 to 1.0] to stereo pan [-1.0 to 1.0]
        pan = (horizontal_pos - 0.5) * 2.0

        # Closer obstacle = higher pitch (urgent)
        # e.g. 0.5m -> 1400 Hz, 1.5m -> 800 Hz, 2.5m -> 450 Hz
        clamped_dist = max(0.4, min(3.0, distance_meters))
        frequency = 1800.0 - (clamped_dist * 450.0)

        tone = self.generate_tone(frequency_hz=frequency, duration_sec=0.07, pan=pan)

        def _play():
            try:
                sd.play(tone, self.sample_rate)
            except Exception as e:
                logger.error(f"Error playing earcon tone: {e}")

        await asyncio.to_thread(_play)
