"""Text-to-Speech engine with multiple backends.

Supports:
1. Piper TTS (primary) — Fast, natural-sounding, runs locally
2. pyttsx3 (fallback) — Works everywhere, sounds robotic

The engine uses a priority queue so critical safety alerts
(e.g., 'Obstacle ahead!') interrupt less important speech.
"""

import asyncio
import logging
import os
import queue
import threading
import sounddevice as sd
import numpy as np
from enum import IntEnum, Enum

logger = logging.getLogger(__name__)

class Priority(IntEnum):
    """Priority levels for speech messages."""
    CRITICAL = 0   # Obstacles, imminent danger
    HIGH = 1       # Navigation instructions
    NORMAL = 2     # Scene description
    LOW = 3        # General info, battery status

class TTSMessage:
    """Represents a speech message in the queue."""
    def __init__(self, text: str, priority: Priority):
        self.text = text
        self.priority = priority

    def __lt__(self, other):
        # Priority queue sorts by lowest priority value first
        return self.priority < other.priority

class TTSBackend(Enum):
    """Supported text-to-speech backends."""
    KOKORO = "kokoro"   # SOTA human-grade neural voice (82M params)
    PIPER = "piper"     # Ultra-fast edge neural voice
    PYTTSX3 = "pyttsx3" # Universal offline fallback

class TTSEngine:
    """Text-to-speech engine with priority queuing and multiple backends."""

    def __init__(self, rate: int = 150, volume: float = 1.0, backend: str = 'auto'):
        """
        Initialize the TTS engine.
        
        Args:
            rate (int): Speech rate (words per minute). Applies mainly to pyttsx3.
            volume (float): Speech volume (0.0 to 1.0).
            backend (str): TTS backend to use: 'auto', 'kokoro', 'piper', or 'pyttsx3'.
        """
        self.rate = rate
        self.volume = volume
        self._queue = queue.PriorityQueue()
        self._is_running = False
        self._stop_current = threading.Event()
        self._thread = None
        self._engine = None
        
        self.backend_type = None
        self._piper_voice = None
        self._kokoro_pipeline = None
        
        self._setup_backend(backend)

    def _setup_backend(self, requested_backend: str):
        """Detect and set up the best available TTS backend (Kokoro -> Piper -> pyttsx3)."""
        if requested_backend in ('auto', 'kokoro'):
            try:
                import kokoro
                self.backend_type = TTSBackend.KOKORO
                logger.info("Kokoro-82M SOTA neural TTS backend selected.")
                return
            except ImportError:
                if requested_backend == 'kokoro':
                    logger.warning("Kokoro requested but not installed. Falling back...")

        if requested_backend in ('auto', 'piper'):
            try:
                import piper
                self.backend_type = TTSBackend.PIPER
                logger.info("Piper TTS backend selected.")
                return
            except ImportError:
                if requested_backend == 'piper':
                    logger.warning("Piper TTS requested but not installed. Falling back to pyttsx3.")

        self.backend_type = TTSBackend.PYTTSX3
        logger.info("pyttsx3 TTS backend selected.")

    def _init_piper(self):
        """Initialize Piper TTS voice model."""
        import piper
        
        # Determine paths for Piper models
        data_dir = os.path.expanduser("~/.local/share/piper/voices/")
        os.makedirs(data_dir, exist_ok=True)
        
        model_name = "en_US-lessac-medium"
        model_path = os.path.join(data_dir, f"{model_name}.onnx")
        config_path = os.path.join(data_dir, f"{model_name}.onnx.json")
        
        # If model doesn't exist, this should theoretically download it or we assume it's pre-downloaded
        # For this implementation, we assume the model files are managed externally if they don't exist,
        # but we handle the loading.
        if not os.path.exists(model_path):
            logger.warning(f"Piper model not found at {model_path}. Please download it.")
            # Fallback to pyttsx3 if Piper model is missing during thread init
            raise FileNotFoundError(f"Missing Piper model: {model_path}")
            
        self._piper_voice = piper.PiperVoice.load(model_path, config_path)
        logger.info(f"Loaded Piper voice model: {model_name}")

    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine."""
        import pyttsx3
        self._engine = pyttsx3.init()
        self._engine.setProperty('rate', self.rate)
        self._engine.setProperty('volume', self.volume)

    def _init_kokoro(self):
        """Initialize Kokoro-82M neural TTS pipeline."""
        from kokoro import KPipeline
        self._kokoro_pipeline = KPipeline(lang_code='a')
        logger.info("Loaded Kokoro-82M neural TTS pipeline.")

    def start(self):
        """Start the background TTS processing thread."""
        if self._is_running:
            return
        
        self._is_running = True
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()
        logger.info("TTS engine started.")

    def _process_queue(self):
        """Worker function for the background thread."""
        try:
            if self.backend_type == TTSBackend.KOKORO:
                try:
                    self._init_kokoro()
                except Exception as e:
                    logger.error(f"Failed to initialize Kokoro ({e}), falling back to Piper...")
                    self.backend_type = TTSBackend.PIPER

            if self.backend_type == TTSBackend.PIPER:
                try:
                    self._init_piper()
                except Exception as e:
                    logger.error(f"Failed to initialize Piper ({e}), falling back to pyttsx3...")
                    self.backend_type = TTSBackend.PYTTSX3
                    self._init_pyttsx3()
            elif self.backend_type == TTSBackend.PYTTSX3:
                self._init_pyttsx3()
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
            self._is_running = False
            return

        while self._is_running:
            try:
                # Use a timeout to periodically check if we should stop running
                msg = self._queue.get(timeout=0.5)
                
                if self._stop_current.is_set():
                    self._stop_current.clear()
                    
                logger.debug(f"Speaking (Priority: {msg.priority.name}): {msg.text}")
                
                # Check stop flag before speaking
                if not self._stop_current.is_set():
                    self._speak_message(msg.text)
                        
                self._queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in TTS worker thread: {e}")

    def _speak_message(self, text: str):
        """Speak a single message using the active backend."""
        try:
            if self.backend_type == TTSBackend.KOKORO and self._kokoro_pipeline:
                # High-fidelity Kokoro-82M synthesis (24kHz studio audio)
                generator = self._kokoro_pipeline(text, voice='af_heart')
                for _, _, audio in generator:
                    if self._stop_current.is_set():
                        sd.stop()
                        break
                    sd.play(audio, 24000)
                    sd.wait()

            elif self.backend_type == TTSBackend.PIPER and self._piper_voice:
                # Synthesize audio stream raw gives 16-bit PCM audio bytes
                audio_stream = self._piper_voice.synthesize_stream_raw(text)
                sample_rate = self._piper_voice.config.sample_rate
                
                def play_stream():
                    with sd.RawOutputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
                        for chunk in audio_stream:
                            if self._stop_current.is_set():
                                break
                            stream.write(chunk)
                
                play_stream()
                
            else:
                # pyttsx3 fallback
                if self._engine:
                    self._engine.say(text)
                    self._engine.runAndWait()
        except Exception as e:
            logger.error(f"Error during speech generation: {e}")

    async def speak(self, text: str, priority: Priority = Priority.NORMAL):
        """
        Queue text to be spoken.
        
        Args:
            text (str): The text to speak.
            priority (Priority): The urgency of the message.
        """
        if not self._is_running:
            logger.warning("TTS engine is not running, message discarded.")
            return

        if priority == Priority.CRITICAL:
            self.stop() # Interrupt current speech
            
        msg = TTSMessage(text, priority)
        self._queue.put(msg)
        logger.debug(f"Queued speech: '{text}' with priority {priority.name}")

    def stop(self):
        """Stop the currently playing speech immediately."""
        logger.info("Stopping current speech.")
        self._stop_current.set()
        
        # Stop pyttsx3 engine if it's currently running
        if self.backend_type == TTSBackend.PYTTSX3 and self._engine:
             try:
                 self._engine.stop()
             except Exception as e:
                 logger.error(f"Failed to stop pyttsx3 engine: {e}")

    def shutdown(self):
        """Shut down the TTS engine and release resources."""
        logger.info("Shutting down TTS engine.")
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)
