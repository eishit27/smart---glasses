"""
VisionAid Edge Model Optimization & Export Pipeline
===================================================

Exports trained models into high-performance edge execution formats:
1. ONNX (Cross-platform standard)
2. OpenVINO (Accelerates inference 3x–5x on Intel i7 CPUs & Iris Xe)
3. TFLite (Android / ARM edge accelerators with INT8 quantization)

Usage:
    python training/export_edge.py --weights server/models/hazard_yolo11.pt --format openvino
    python training/export_edge.py --weights server/models/hazard_yolo11.pt --format onnx
    python training/export_edge.py --weights server/models/hazard_yolo11.pt --format tflite
"""

import os
import argparse
import logging

logger = logging.getLogger("ExportEdge")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def export_model(weights_path: str, export_format: str = "openvino", imgsz: int = 640):
    """
    Exports a trained YOLO model to target format.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("Ultralytics not installed. Run: pip install ultralytics")
        return

    if not os.path.exists(weights_path):
        logger.warning(f"Weights file {weights_path} not found. Attempting to export base yolo11n.pt...")
        weights_path = "yolo11n.pt"

    logger.info("=" * 60)
    logger.info(f"  Exporting Model: {weights_path}")
    logger.info(f"  Target Format:   {export_format.upper()}")
    logger.info("=" * 60)

    model = YOLO(weights_path)

    # Ultralytics export handles ONNX, OpenVINO, CoreML, TFLite natively
    exported_path = model.export(
        format=export_format,
        imgsz=imgsz,
        half=True if export_format in ['onnx', 'openvino'] else False,
        int8=True if export_format == 'tflite' else False
    )

    logger.info(f"✅ Successfully exported model to: {exported_path}")
    return exported_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export VisionAid model for edge acceleration")
    parser.add_argument('--weights', type=str, default="server/models/hazard_yolo11.pt", help="Path to weights file")
    parser.add_argument('--format', type=str, choices=['onnx', 'openvino', 'tflite'], default='onnx', help="Export format")
    args = parser.parse_args()

    export_model(args.weights, args.format)
