"""
VisionAid Smart Glasses — Main Server (Hybrid Architecture)
=============================================================

This is the brain of the VisionAid system. It uses a dual-path architecture:

⚡ FAST PATH (every frame, ~30ms, no internet):
    YOLO object detection + Depth estimation → instant safety alerts

🧠 SMART PATH (on command, needs internet):
    Gemini Vision API → rich contextual scene descriptions

This means safety-critical features ALWAYS work, even offline.

Usage:
    python main.py --mode webcam            # Test with laptop webcam
    python main.py --mode ble               # Connect to glasses via BLE
    python main.py --mode wifi              # Connect via WiFi
    python main.py --mode webcam --offline   # Force offline mode (no Gemini)
"""

import asyncio
import argparse
import logging
import signal
import sys
from typing import AsyncGenerator, Optional

import cv2
import numpy as np

from config import Config

# Communication receivers
from comms import BLEReceiver, WiFiReceiver

# Hybrid vision pipeline (local + cloud AI)
from vision.hybrid_pipeline import HybridVisionPipeline

# Audio output and input
from audio.tts_engine import TTSEngine, Priority
from audio.speech_recognizer import SpeechRecognizer

# Storage
from storage.recorder import Recorder

# Voice commands
from commands.voice_handler import VoiceCommandHandler, CommandType

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VisionAid")


class VisionAidServer:
    """
    Core server orchestrating all VisionAid subsystems.

    Architecture:
        Frame Source (webcam/BLE/WiFi)
              ↓
        Hybrid Vision Pipeline
         ├─ Fast Path: YOLO + Depth (local, every frame)
         └─ Smart Path: Gemini (cloud, on command)
              ↓
        Priority TTS Queue → Bone Conduction Speaker
    """

    def __init__(self, config: Config, mode: str, offline: bool = False):
        self.config = config
        self.mode = mode
        self.running = False
        self._current_frame: Optional[np.ndarray] = None

        # Force offline mode if requested
        if offline:
            config.gemini_api_key = None
            logger.info("Running in OFFLINE mode — Gemini features disabled.")

        # ── Initialise subsystems ──────────────────────────────────────
        logger.info("=" * 60)
        logger.info("    VisionAid Smart Glasses — Initializing")
        logger.info("=" * 60)

        # Audio output and input
        self.tts = TTSEngine(
            rate=config.audio.speech_rate,
            volume=config.audio.volume,
        )

        # Fast-Motion & Running Protection Engine
        from vision.running_mode import MotionAdaptiveSafetyEngine
        from vision.metric_depth import MetricDepthCalibrator
        from vision.tracker import ObstacleTracker
        from audio.earcons import EarconGenerator

        self.motion_engine = MotionAdaptiveSafetyEngine()
        self.metric_calibrator = MetricDepthCalibrator()
        self.tracker = ObstacleTracker(alert_cooldown_sec=3.0)
        self.earcons = EarconGenerator()

        # Cognitive Assistant (Visual Working Memory + Specialized Skills + Pathfinder)
        from intelligence.assistant import CognitiveAssistant
        self.assistant = CognitiveAssistant()
        self._last_detections: List[Dict[str, Any]] = []

        # Speech recognition (faster-whisper, runs locally)
        self.speech = SpeechRecognizer(model_size='base', language='en')

        # Hybrid vision pipeline — the brain
        # Automatically uses local models (YOLO, Depth, EasyOCR, face_recognition)
        # and adds Gemini cloud AI when API key is available
        self.vision = HybridVisionPipeline(config)

        # Recording & storage
        self.recorder = Recorder(
            base_dir=config.storage.recordings_dir,
            max_storage_gb=5.0,
        )

        # Voice commands
        self.voice_handler = VoiceCommandHandler()

        # Processing state
        self._continuous_nav = False
        self._frame_counter = 0
        self._fast_scan_interval = 4     # run fast scan every Nth frame
        self._voice_listen_task = None

        # Report capabilities
        caps = self.vision.capabilities
        logger.info("Available capabilities:")
        for cap, available in caps.items():
            status = "✅" if available else "❌ (offline)"
            logger.info(f"  {status}  {cap}")
        logger.info("=" * 60)

    # ── Frame Sources ──────────────────────────────────────────────────

    async def webcam_generator(self) -> AsyncGenerator[bytes, None]:
        """Yield JPEG frames from the laptop webcam (for testing)."""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera.resolution[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera.resolution[1])

        if not cap.isOpened():
            logger.error("Failed to open webcam.")
            await self.tts.speak("Camera not available.", Priority.CRITICAL)
            return

        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    await asyncio.sleep(0.1)
                    continue

                _, buffer = cv2.imencode(
                    '.jpg', frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), self.config.camera.jpeg_quality]
                )
                yield buffer.tobytes()
                await asyncio.sleep(1.0 / self.config.camera.fps)
        finally:
            cap.release()

    # ── Frame Processing Pipeline ──────────────────────────────────────

    async def process_frame(self, frame_bytes: bytes):
        """
        Central processing pipeline for a single camera frame.

        Every frame: decode + optional fast scan (YOLO + Depth)
        On command: full Gemini analysis, OCR, face recognition
        """
        # Decode JPEG → numpy array
        np_arr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return

        self._current_frame = frame
        self._frame_counter += 1

        # If recording, add frame to video
        if self.recorder._is_recording:
            await self.recorder.add_frame_to_video(frame)

        # ── Dynamic Motion & Velocity Assessment ───────────────────
        motion_state = self.motion_engine.estimate_motion(frame)
        safety_horizon = motion_state["safety_horizon_m"]
        is_running = motion_state["is_running"]

        # If user is running, turbo mode increases sampling rate
        scan_interval = 2 if is_running else self._fast_scan_interval

        # ── Fast Path: local YOLO + Depth (runs dynamically) ───────
        if self._frame_counter % scan_interval == 0:
            try:
                scan = await self.vision.fast_scan(frame)

                # Prepare detections for tracking & metric conversion
                det_dicts = []
                for d in scan.detections:
                    dist = d.distance if (d.distance and d.distance > 0.1) else 2.8
                    det_dicts.append({
                        'label': d.label,
                        'bbox': d.bbox,
                        'distance_meters': dist,
                        'center_x': (d.bbox[0] + d.bbox[2]) / (2.0 * frame.shape[1])
                    })

                self._last_detections = det_dicts
                proactive_event = self.assistant.update_world_state(det_dicts, scan.spatial_description, frame.shape)
                if proactive_event and proactive_event.get("message"):
                    await self.tts.speak(proactive_event["message"], Priority.HIGH)

                # Update tracker with Time-to-Collision (TTC) & de-bouncing
                active_obstacles = self.tracker.update(det_dicts)

                # Filter urgent hazards based on walking vs running horizon
                critical_hazards = self.motion_engine.filter_urgent_running_hazards(active_obstacles, safety_horizon)

                for item in critical_hazards:
                    obs = item["obstacle"]
                    # 1. Fire Instant Directional Audio Earcon (<25ms acoustic radar)
                    await self.earcons.play_proximity_cue(obs.distance_meters, obs.center_x)

                    # 2. Spoken Alert (concise for runners)
                    if is_running:
                        msg = f"STOP: {obs.label} {obs.distance_meters:.1f} meters!"
                        await self.tts.speak(msg, Priority.CRITICAL)
                    else:
                        msg = f"Caution: {obs.label} {obs.distance_meters:.1f}m ahead"
                        await self.tts.speak(msg, Priority.HIGH)

                # Drop-offs, stairs down, or curb warnings from depth map
                for hazard in scan.hazards:
                    await self.earcons.play_proximity_cue(0.7, 0.5)
                    await self.tts.speak(hazard, Priority.CRITICAL)

                # Continuous navigation cues when walking
                if self._continuous_nav and not is_running and scan.spatial_description:
                    await self.tts.speak(scan.spatial_description, Priority.NORMAL)

                if scan.processing_time_ms > 0:
                    logger.debug(
                        f"Scan: {scan.processing_time_ms:.0f}ms | "
                        f"Speed: {motion_state['estimated_speed_mps']}m/s | "
                        f"Horizon: {safety_horizon}m"
                    )
            except Exception as e:
                logger.error(f"Fast scan failed: {e}")

    # ── Command Handlers ───────────────────────────────────────────────

    async def handle_command(self, command_type: CommandType):
        """Execute a user command against the current frame."""
        frame = self._current_frame
        if frame is None:
            await self.tts.speak("No camera frame available yet.", Priority.HIGH)
            return

        if command_type == CommandType.DESCRIBE_SCENE:
            await self.tts.speak("Analyzing scene...", Priority.NORMAL)
            description = await self.vision.full_describe(frame)
            await self.tts.speak(description, Priority.NORMAL)

        elif command_type == CommandType.READ_TEXT:
            await self.tts.speak("Reading text...", Priority.NORMAL)
            result = await self.vision.read_text(frame)
            text = result.get("text", "No text found.")
            context = result.get("context", "")
            speech = f"{context}: {text}" if context else text
            await self.tts.speak(speech, Priority.NORMAL)

        elif command_type == CommandType.IDENTIFY_PERSON:
            await self.tts.speak("Looking for faces...", Priority.NORMAL)
            faces = await self.vision.identify_faces(frame)
            if not faces:
                await self.tts.speak("No faces detected.", Priority.NORMAL)
            else:
                for face in faces:
                    name = face.get("name", "Unknown person")
                    location = face.get("location", "")
                    await self.tts.speak(f"{name}, {location}.", Priority.NORMAL)

        elif command_type == CommandType.NAVIGATE:
            self._continuous_nav = not self._continuous_nav
            state = "enabled" if self._continuous_nav else "disabled"
            await self.tts.speak(f"Navigation mode {state}.", Priority.HIGH)
            if self._continuous_nav:
                # Run an immediate navigation analysis
                nav = await self.vision.navigate(frame)
                await self.tts.speak(nav.directions, Priority.NORMAL)

        elif command_type == CommandType.TAKE_PHOTO:
            path = await self.recorder.save_frame(frame)
            await self.tts.speak("Photo saved.", Priority.LOW)

        elif command_type == CommandType.RECORD_VIDEO:
            if self.recorder._is_recording:
                path = await self.recorder.stop_recording()
                await self.tts.speak("Recording saved.", Priority.NORMAL)
            else:
                h, w = frame.shape[:2]
                await self.recorder.start_recording(fps=10, frame_size=(w, h))
                await self.tts.speak("Recording started.", Priority.HIGH)

        elif command_type == CommandType.STOP_RECORDING:
            path = await self.recorder.stop_recording()
            if path:
                await self.tts.speak("Recording saved.", Priority.NORMAL)
            else:
                await self.tts.speak("Not currently recording.", Priority.LOW)

        elif command_type == CommandType.HELP:
            help_text = (
                "Available commands: "
                "Say 'describe' for scene description. "
                "Say 'read' to read text. "
                "Say 'who is this' to identify people. "
                "Say 'navigate' to toggle navigation. "
                "Say 'take photo' to save a picture. "
                "Say 'record' to start or stop recording."
            )
            await self.tts.speak(help_text, Priority.LOW)

    # ── Voice Listening Loop ───────────────────────────────────────────

    async def voice_listening_loop(self):
        """
        Continuously listen for voice commands in the background.

        Listens for 3-second chunks, checks for wake word,
        then processes the command.
        """
        logger.info("Voice listening loop started. Say 'Hey Vision' to activate.")
        while self.running:
            try:
                # Listen for a short chunk
                text = await self.speech.listen_and_recognize(duration=3.0)
                if not text:
                    continue

                logger.info(f"Heard: '{text}'")

                # Check for wake word or just process directly
                # For accessibility, we skip wake word and process any command
                command = self.voice_handler.process_command(text)
                if command.type not in (CommandType.UNKNOWN, CommandType.CONVERSATIONAL_QUERY):
                    logger.info(f"Voice shortcut triggered: {command.type.name}")
                    await self.handle_command(command.type)
                else:
                    # Genuinely Smart Alexa-style Conversational Visual AI!
                    # Handles: "What am I holding?", "Where did I put my keys?", "Is this milk expired?", "Is anyone smiling?"
                    query_text = command.clean_query if command.clean_query else text
                    logger.info(f"Routing conversational query to Cognitive Assistant: '{query_text}'")
                    ocr_res = await self.vision.read_text(self._current_frame) if self._current_frame is not None else {}
                    ocr_text = ocr_res.get("text", "")

                    smart_answer = await self.assistant.answer_smart_query(
                        query=query_text,
                        current_frame=self._current_frame if self._current_frame is not None else np.zeros((480, 640, 3), dtype=np.uint8),
                        current_detections=self._last_detections,
                        ocr_text=ocr_text,
                        vlm_engine=self.vision.local_vlm
                    )
                    await self.tts.speak(smart_answer, Priority.NORMAL)

            except Exception as e:
                logger.error(f"Voice listening error: {e}")
                await asyncio.sleep(1.0)

    # ── Button Events from ESP32 ───────────────────────────────────────

    async def handle_button_event(self, event_code: int):
        """Map ESP32 button events to commands."""
        event_map = {
            1: CommandType.DESCRIBE_SCENE,    # single press
            2: CommandType.READ_TEXT,          # double press
            3: CommandType.IDENTIFY_PERSON,    # triple press
            4: CommandType.RECORD_VIDEO,       # long press (toggle)
        }
        cmd = event_map.get(event_code)
        if cmd:
            await self.handle_command(cmd)

    # ── Main Run Loop ──────────────────────────────────────────────────

    async def run(self):
        """Start the server and begin processing frames."""
        self.running = True
        self.tts.start()
        logger.info(f"Starting VisionAid in '{self.mode}' mode...")

        try:
            # Select frame source
            if self.mode == 'webcam':
                frame_gen = self.webcam_generator()
            elif self.mode == 'ble':
                receiver = BLEReceiver(self.config.ble)
                frame_gen = receiver.receive_frames()
                asyncio.create_task(receiver.connect_and_run())
            elif self.mode == 'wifi':
                receiver = WiFiReceiver(port=8080)
                frame_gen = receiver.receive_frames()
                asyncio.create_task(receiver.start_server())
            else:
                logger.error(f"Invalid mode: {self.mode}")
                return

            # Start voice listening in background
            self._voice_listen_task = asyncio.create_task(
                self.voice_listening_loop()
            )

            online_status = "Online (Gemini + local AI)" if self.vision.is_online else "Offline (local AI only)"
            await self.tts.speak(
                f"Vision Aid ready. {online_status}. "
                "Press button or speak a command.",
                Priority.NORMAL,
            )

            # Main frame processing loop
            async for frame_bytes in frame_gen:
                if not self.running:
                    break
                await self.process_frame(frame_bytes)

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            await self.tts.speak("System error. Please restart.", Priority.CRITICAL)
        finally:
            self.running = False
            if self._voice_listen_task:
                self._voice_listen_task.cancel()
            await self.recorder.stop_recording()
            self.tts.shutdown()
            logger.info("Server shut down.")

    def stop(self):
        """Signal the server to stop gracefully."""
        logger.info("Shutdown signal received.")
        self.running = False


# ── Entry Point ────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description="VisionAid Smart Glasses Server — Hybrid AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode webcam              # Test with laptop webcam
  python main.py --mode webcam --offline    # Offline mode (YOLO + Depth only)
  python main.py --mode ble                 # Connect to glasses via Bluetooth
  python main.py --mode wifi                # Connect via WiFi
        """,
    )
    parser.add_argument(
        '--mode',
        choices=['ble', 'wifi', 'webcam'],
        default='webcam',
        help="Frame source: 'webcam' for testing, 'ble' or 'wifi' for glasses",
    )
    parser.add_argument(
        '--offline',
        action='store_true',
        help="Run in offline mode (no cloud API, local models only)",
    )
    args = parser.parse_args()

    # Load .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    config = Config()
    server = VisionAidServer(config, args.mode, offline=args.offline)

    # Graceful shutdown on Ctrl+C
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, server.stop)

    await server.run()


if __name__ == '__main__':
    asyncio.run(main())
