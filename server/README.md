# VisionAid Python Server

This component handles receiving images from the BLE device and communicating with the Gemini AI models for computer vision and OCR.

## Requirements

- Python 3.11+
- Bluetooth LE compatible adapter (if running on laptop/PC)

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install bleak pillow google-generativeai python-dotenv
   ```
3. Set your Gemini API key:
   Create a `.env` file in this directory:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

## Running

**BLE Mode (Production)**
Connects to the ESP32 via BLE to receive frame chunks, reconstruct them, and process through AI.
```bash
python server.py --mode ble
```

**Webcam Mode (Testing)**
If you don't have the ESP32 flashed yet, you can test the AI prompt logic using your laptop's webcam.
```bash
python server.py --mode webcam
```

## Configuration
Modify `config.yaml` to adjust prompt verbosity, language output, and model parameters.
