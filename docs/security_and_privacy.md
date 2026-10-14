# VisionAid Smart Glasses — Security, Anti-Hacking & Privacy Architecture

As an assistive wearable device for the blind and visually impaired, **security and privacy are life-safety requirements**, not optional features. If an attacker tampers with navigation signals or eavesdrops on camera feeds, the user's physical safety and personal privacy are at direct risk.

---

## 1. Threat Model & Protections

| Threat Vector | Attack Scenario | VisionAid Defense Mechanism |
|---|---|---|
| **Eavesdropping on Video Stream** | Attacker nearby uses BLE/WiFi sniffer to spy on the user's private surroundings, home, or documents. | **Encrypted Transmissions & Authenticated Sessions**: Video frames are gated behind a cryptographic token handshake (`AUTH:<token>`). Unauthenticated clients receive 0 frames. |
| **Malicious Navigation Spoofing** | Attacker injects fake audio commands telling the blind user "Path is clear" towards traffic or stairs. | **Air-Gapped Local Safety Priority**: Local YOLOv8 + Depth Anything runs independently in the offline loop. It has absolute priority over network inputs and cannot be remotely suppressed. |
| **Rogue Bluetooth Pairing** | Stranger in public tries pairing their phone to the glasses to hijack control. | **10-Second Auto-Disconnect**: If a connected BLE client does not authenticate with the pre-shared pairing secret within 10 seconds, the ESP32 terminates the connection immediately. |
| **Biometric & Recording Theft** | Device or companion phone is lost or stolen; thief dumps photos or facial database of friends/family. | **AES-256-GCM Storage Encryption**: The face database (`face_db.json.enc`) and captured media are encrypted at rest using authenticated AES-256-GCM. |
| **Covert Recording / Bystander Privacy** | Malicious actor tries using the glasses as a covert spy camera with the indicator LED covered or turned off. | **Hardware LED Interlock & Tamper Detection**: Optical sensor verifies LED illumination; MOSFET circuit physically ties camera power to the LED rail. |
| **Firmware Tampering / Dumping** | Attacker extracts proprietary firmware or credentials via serial flasher. | **ESP32-S3 Hardware Secure Boot & Flash Encryption**: Firmware can be locked into ESP32-S3 eFuses using hardware-accelerated AES-XTS. |

---

## 2. API Key Requirements: Do You Need API Keys?

### Short Answer: **NO! The product does NOT require any API keys to function.**

Because VisionAid uses a **hybrid open-source architecture**, all primary safety and perception features run **100% locally on-device / on the companion phone**:

| Feature | Engine | API Key Needed? | Internet Needed? |
|---|---|---|---|
| **Obstacle & Danger Alerts** | YOLOv8n (Local) | ❌ **No** | ❌ **No (Offline)** |
| **Distance & Depth Estimation** | Depth Anything v2 (Local) | ❌ **No** | ❌ **No (Offline)** |
| **Text & Sign Reading (OCR)** | EasyOCR (Local) | ❌ **No** | ❌ **No (Offline)** |
| **Face Recognition** | face_recognition / dlib (Local) | ❌ **No** | ❌ **No (Offline)** |
| **Voice Commands & Recognition** | faster-whisper (Local) | ❌ **No** | ❌ **No (Offline)** |
| **Text-to-Speech Output** | Piper TTS (Local) | ❌ **No** | ❌ **No (Offline)** |
| **Photo & Video Recording** | Local Encrypted Storage | ❌ **No** | ❌ **No (Offline)** |
| **Rich Scene Descriptions** | Google Gemini 2.5 Flash | ⚠️ **Optional** | 🌐 Only for cloud descriptions |

### When WOULD you use an API key?
- Only if you specifically enable the **Cloud Enhancement Mode** to ask Gemini deep contextual questions like:
  - *"Describe the general architecture and vibe of this room."*
  - *"Which dishes on this menu are gluten-free?"*
- Even for that, Google AI Studio provides a free tier.

### For Commercial Production:
When shipping a consumer product to blind users:
1. **Best Route (Zero Ongoing Cost & Max Privacy)**: Ship 100% in **Offline Mode**. Users never worry about internet outages, subscriptions, or API bills.
2. **Hybrid Cloud Route**: If cloud features are offered, your companion app talks to your own backend server that manages cloud inference. **End users NEVER type in or manage API keys.**

---

## 3. Cryptographic Implementation Details

### Data at Rest: AES-256-GCM
Implemented in [`server/security/crypto.py`](file:///home/eishit/Documents/glasses/server/security/crypto.py):
- **Algorithm**: Advanced Encryption Standard in Galois/Counter Mode (AES-GCM).
- **Key Length**: 256 bits.
- **Nonce**: 96-bit cryptographically secure random bytes generated per write operation (`os.urandom(12)`).
- **Integrity Tag**: 128-bit authentication tag guarantees that tampered or corrupted files are immediately rejected.

### Data in Transit: Mutual Authentication
- **BLE**: [`firmware/src/ble_comm.cpp`](file:///home/eishit/Documents/glasses/firmware/src/ble_comm.cpp) enforces bonding, encryption, and an authenticated handshake (`AUTH:<pairing_token>`).
- **WiFi**: [`server/comms/wifi_receiver.py`](file:///home/eishit/Documents/glasses/server/comms/wifi_receiver.py) rejects all incoming HTTP POST and WebSocket requests without a matching `Authorization: Bearer <token>` header.

### Firmware Hardening on ESP32-S3
The Seeed XIAO ESP32-S3 Sense includes hardware cryptographic engines:
1. **Flash Encryption (AES-XTS-128 / 256)**: Encrypts external SPI flash so firmware and captured frames cannot be read by physical chip probes.
2. **Secure Boot v2 (RSA-3072 / ECDSA)**: Cryptographically verifies the digital signature of firmware binaries on every boot, preventing rootkits or unauthorized modifications.
