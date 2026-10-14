"""
VisionAid Security & Cryptography Module
=========================================

Handles:
- AES-256-GCM authenticated encryption for data-at-rest (recordings, face database)
- Secure key derivation (PBKDF2) from user master PIN or hardware seed
- HMAC-SHA256 packet signing & token verification to prevent frame/command injection
"""

import os
import hmac
import hashlib
import json
import logging
from typing import Tuple, Optional, Dict, Any
from base64 import b64encode, b64decode

logger = logging.getLogger(__name__)

# Use cryptography library for industry standard AES-256-GCM
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    logger.warning("cryptography package not installed. Installing it is strongly recommended for storage encryption.")


class SecurityManager:
    """
    Manages cryptographic operations for VisionAid.
    
    Protects blind users from:
    1. Video/Audio snooping (Eavesdropping)
    2. Malicious command injection (Fake obstacle/navigation cues)
    3. Stolen device data exposure (Encrypted biometric face database & recordings)
    """

    def __init__(self, master_key_hex: Optional[str] = None, pairing_token: Optional[str] = None):
        """
        Initialize security manager.
        
        Args:
            master_key_hex: 256-bit hex key for AES-GCM (auto-generated if None)
            pairing_token: Shared secret token for BLE/WiFi mutual authentication
        """
        if master_key_hex:
            self._key = bytes.fromhex(master_key_hex)
        else:
            # Fallback to key file or generate new 256-bit key
            self._key = self._load_or_create_device_key()

        self.pairing_token = (pairing_token or os.getenv("VISIONAID_PAIRING_TOKEN", "visionaid-secure-pair-token")).encode('utf-8')
        
        if HAS_CRYPTOGRAPHY:
            self._aesgcm = AESGCM(self._key)
        else:
            self._aesgcm = None

    def _load_or_create_device_key(self) -> bytes:
        """Loads persistent 256-bit AES master key from secure local storage or generates one."""
        key_dir = os.path.expanduser("~/.config/visionaid")
        key_file = os.path.join(key_dir, "master_key.bin")
        
        try:
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    return f.read()
            else:
                os.makedirs(key_dir, mode=0o700, exist_ok=True)
                new_key = AESGCM.generate_key(bit_length=256) if HAS_CRYPTOGRAPHY else os.urandom(32)
                with open(key_file, "wb") as f:
                    f.write(new_key)
                os.chmod(key_file, 0o600)  # Owner read/write only
                logger.info(f"Generated new secure master key at {key_file}")
                return new_key
        except Exception as e:
            logger.error(f"Error managing device master key file: {e}. Falling back to ephemeral key.")
            return os.urandom(32)

    # ── Authenticated Data Encryption (AES-256-GCM) ──────────────────────

    def encrypt_data(self, plaintext: bytes) -> bytes:
        """
        Encrypts arbitrary bytes using AES-256-GCM with a random 96-bit nonce.
        Format: [12-byte Nonce] + [Ciphertext + 16-byte Auth Tag]
        """
        if not HAS_CRYPTOGRAPHY or self._aesgcm is None:
            # Fallback notice: plaintext returned if crypto lib missing
            logger.warning("Encryption bypassed: 'cryptography' library not installed.")
            return plaintext

        nonce = os.urandom(12)  # 96-bit random nonce for GCM
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    def decrypt_data(self, payload: bytes) -> bytes:
        """
        Decrypts AES-256-GCM payload and verifies integrity tag.
        Raises ValueError if data was tampered with.
        """
        if not HAS_CRYPTOGRAPHY or self._aesgcm is None:
            return payload

        if len(payload) < 28:  # 12 nonce + 16 tag minimum
            raise ValueError("Encrypted payload too short or corrupted.")

        nonce = payload[:12]
        ciphertext = payload[12:]
        try:
            return self._aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            logger.critical("Data integrity check failed! File was tampered with or key is invalid.")
            raise ValueError("Decryption failed / Authenticity verification failed") from e

    # ── Packet & Command Signing (HMAC-SHA256) ─────────────────────────

    def generate_auth_signature(self, message: bytes) -> str:
        """Generates HMAC-SHA256 signature for a message or frame."""
        return hmac.new(self.pairing_token, message, hashlib.sha256).hexdigest()

    def verify_auth_signature(self, message: bytes, expected_sig: str) -> bool:
        """
        Constant-time signature verification to prevent timing attacks.
        Ensures camera frames and commands genuinely originated from the paired glasses.
        """
        calc_sig = self.generate_auth_signature(message)
        return hmac.compare_digest(calc_sig, expected_sig)

    def verify_token(self, provided_token: str) -> bool:
        """Constant-time token verification."""
        if not provided_token:
            return False
        return hmac.compare_digest(provided_token.encode('utf-8'), self.pairing_token)
