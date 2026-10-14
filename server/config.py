import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CameraConfig:
    resolution: tuple[int, int] = (640, 480)
    fps: int = 15
    jpeg_quality: int = 80

@dataclass
class AudioConfig:
    tts_engine: str = "piper"  # Default to high quality Piper TTS
    speech_rate: int = 150
    volume: float = 1.0

@dataclass
class BLEConfig:
    # Must match firmware/src/ble_comm.cpp
    service_uuid: str = os.getenv("BLE_SERVICE_UUID", "4fafc201-1fb5-459e-8fcc-c5c9c331914b")
    tx_char_uuid: str = os.getenv("BLE_TX_CHAR_UUID", "beb5483f-36e1-4688-b7f5-ea07361b26a8")
    rx_char_uuid: str = os.getenv("BLE_RX_CHAR_UUID", "beb5483e-36e1-4688-b7f5-ea07361b26a8")
    mtu: int = int(os.getenv("BLE_MTU", "500"))

@dataclass
class StorageConfig:
    recordings_dir: str = os.getenv("RECORDINGS_DIR", "./data/recordings")
    face_db_dir: str = os.getenv("FACE_DB_DIR", "./data/faces")
    encrypt_storage: bool = os.getenv("ENCRYPT_LOCAL_STORAGE", "true").lower() == "true"

@dataclass
class SecurityConfig:
    pairing_token: str = os.getenv("VISIONAID_PAIRING_TOKEN", "visionaid-secure-pair-token")
    enforce_auth: bool = True

@dataclass
class FeatureFlags:
    enable_scene_description: bool = os.getenv("ENABLE_SCENE_DESC", "true").lower() == "true"
    enable_ocr: bool = os.getenv("ENABLE_OCR", "true").lower() == "true"
    enable_face_recognition: bool = os.getenv("ENABLE_FACE_RECOG", "true").lower() == "true"
    enable_navigation: bool = os.getenv("ENABLE_NAV", "true").lower() == "true"

@dataclass
class Config:
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    camera: CameraConfig = field(default_factory=CameraConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    ble: BLEConfig = field(default_factory=BLEConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)
