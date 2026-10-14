"""Speech recognition using faster-whisper for voice commands.

Runs entirely on-device using CTranslate2-optimized Whisper models.
Faster and more memory-efficient than OpenAI's original whisper.

Used to recognize voice commands like:
- 'Describe what you see'
- 'Read this text'
- 'Who is this person?'
- 'Navigate to the door'
"""

import asyncio
import logging
import numpy as np
import sounddevice as sd
from typing import Optional

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """Voice command recognition using faster-whisper, supporting SOTA large-v3-turbo."""

    def __init__(self, model_size: str = 'base', language: str = 'en', device: str = 'cpu'):
        """
        Initialize the speech recognizer.
        
        Args:
            model_size (str): Model size ('tiny', 'base', 'small', 'large-v3-turbo'). 
                              'large-v3-turbo' offers maximum real-world noise resilience.
            language (str): Language code for recognition.
            device (str): Compute device ('cpu', 'cuda', 'auto').
        """
        # Map shorthand 'turbo' to official faster-whisper model tag
        self.model_size = "deepdml/faster-whisper-large-v3-turbo" if model_size in ('turbo', 'large-v3-turbo') else model_size
        self.language = language
        
        # Auto-detect compute type based on device
        self.device = device
        if self.device == 'cuda' or self.device == 'auto':
            self.compute_type = 'float16' 
            if self.device == 'auto':
                self.compute_type = 'default'
        else:
            self.compute_type = 'int8'
            
        self.model = None
        self._load_lock = asyncio.Lock()

    async def _ensure_model_loaded(self):
        """Ensure the whisper model is loaded and cached."""
        if self.model is None:
            async with self._load_lock:
                if self.model is None:
                    logger.info(f"Loading faster-whisper model '{self.model_size}'...")
                    try:
                        # Run import and load in thread to avoid blocking event loop
                        def load_model():
                            from faster_whisper import WhisperModel
                            return WhisperModel(
                                self.model_size, 
                                device=self.device, 
                                compute_type=self.compute_type
                            )
                            
                        self.model = await asyncio.to_thread(load_model)
                        logger.info("faster-whisper model loaded successfully.")
                    except ImportError:
                        logger.error("faster-whisper not installed. Run: pip install faster-whisper")
                        raise
                    except Exception as e:
                        logger.error(f"Error loading faster-whisper model: {e}")
                        raise

    async def recognize(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        Transcribe raw audio bytes to text.
        
        Args:
            audio_bytes (bytes): Raw audio data (16-bit PCM).
            sample_rate (int): Sample rate of the audio data.
            
        Returns:
            str: Recognized text, or empty string on failure.
        """
        try:
            await self._ensure_model_loaded()
            
            # Convert bytes to numpy float32 array as expected by faster-whisper
            # Assuming 16-bit PCM input
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            
            def transcribe():
                segments, _ = self.model.transcribe(
                    audio_array, 
                    language=self.language, 
                    beam_size=1, 
                    vad_filter=True
                )
                return ' '.join(segment.text for segment in segments).strip()
                
            text = await asyncio.to_thread(transcribe)
            return text
        except Exception as e:
            logger.error(f"Error during speech recognition: {e}")
            return ""

    async def listen_and_recognize(self, duration: float = 3.0, sample_rate: int = 16000) -> str:
        """
        Record from microphone for N seconds and transcribe.
        
        Args:
            duration (float): Seconds to record.
            sample_rate (int): Sample rate for recording.
            
        Returns:
            str: Recognized text, or empty string on failure.
        """
        try:
            logger.info(f"Listening for {duration} seconds...")
            
            def record_audio():
                # Record audio synchronously (in a separate thread)
                recording = sd.rec(
                    int(duration * sample_rate), 
                    samplerate=sample_rate, 
                    channels=1, 
                    dtype='int16'
                )
                sd.wait() # Wait until recording is finished
                return recording.tobytes()

            audio_bytes = await asyncio.to_thread(record_audio)
            
            logger.info("Transcribing audio...")
            text = await self.recognize(audio_bytes, sample_rate=sample_rate)
            return text
            
        except Exception as e:
            logger.error(f"Error during listen and recognize: {e}")
            return ""

    def is_wake_word(self, text: str) -> bool:
        """
        Check if transcribed text contains a wake word.
        
        Args:
            text (str): The recognized text.
            
        Returns:
            bool: True if wake word is found, False otherwise.
        """
        wake_words = ['hey vision', 'vision aid', 'hey glasses']
        text_lower = text.lower().strip()
        
        # Remove common punctuation that whisper might add
        for punct in ['.', ',', '!', '?']:
            text_lower = text_lower.replace(punct, '')
            
        for wake_word in wake_words:
            if wake_word in text_lower:
                return True
                
        return False
