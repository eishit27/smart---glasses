"""
VisionAid YOLO11 Hazard Detector Training Pipeline
==================================================

Trains a specialized, life-safety obstacle detection model for blind pedestrians.
Replaces generic 80-class COCO models with targeted accessibility classes:
- stairs_up, stairs_down, curb, head_hazard, pole_bollard, glass_door, crosswalk

Usage:
    python training/train_yolo_hazards.py --epochs 25 --batch 16 --device cpu
    python training/train_yolo_hazards.py --epochs 100 --batch 32 --device 0  # GPU
"""

import os
import argparse
import shutil
import logging

logger = logging.getLogger("TrainYOLO")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def train_hazard_detector(
    data_yaml: str = "training/datasets/accessibility_hazards/data.yaml",
    base_model: str = "yolo11n.pt",
    epochs: int = 20,
    batch_size: int = 16,
    img_size: int = 640,
    device: str = "cpu",
    output_dir: str = "training/runs/hazard_detector"
):
    """
    Executes training using Ultralytics YOLO11.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("Ultralytics not installed. Run: pip install ultralytics")
        return None

    if not os.path.exists(data_yaml):
        logger.warning(f"Dataset config {data_yaml} not found! Automatically generating bootstrap dataset...")
        from dataset_builder import AccessibilityDatasetBuilder
        builder = AccessibilityDatasetBuilder()
        data_yaml = builder.generate_data_yaml()
        builder.build_dataset(num_train=120, num_val=24, num_test=12)

    logger.info("=" * 60)
    logger.info("  Starting VisionAid Hazard Detector Training")
    logger.info(f"  Base Model:    {base_model}")
    logger.info(f"  Dataset:       {data_yaml}")
    logger.info(f"  Epochs:        {epochs}")
    logger.info(f"  Batch Size:    {batch_size}")
    logger.info(f"  Device:        {device}")
    logger.info("=" * 60)

    # Initialize model with base weights or fallback to yolov8n
    try:
        model = YOLO(base_model)
    except Exception as e:
        logger.warning(f"Could not load {base_model} ({e}), falling back to yolov8n.pt...")
        model = YOLO("yolov8n.pt")

    # Hyperparameters tailored for assistive wearable edge cameras
    train_args = {
        'data': os.path.abspath(data_yaml),
        'epochs': epochs,
        'batch': batch_size,
        'imgsz': img_size,
        'device': device,
        'project': output_dir,
        'name': 'train_run',
        'exist_ok': True,
        'pretrained': True,
        'optimizer': 'AdamW',
        'lr0': 0.002,           # Transfer learning base learning rate
        'lrf': 0.01,
        'warmup_epochs': 2,
        'augment': True,        # Spatial augmentation
        'flipud': 0.0,          # Never flip upside down! Stairs and curbs have definite vertical gravity orientation
        'fliplr': 0.5,          # Horizontal flipping is safe
        'mosaic': 0.8,          # Multi-obstacle scenes
        'mixup': 0.1,
        'val': True,
        'save': True,
        'verbose': True
    }

    results = model.train(**train_args)
    logger.info("Training complete!")

    # Check for best trained weights
    best_weights = os.path.join(output_dir, 'train_run', 'weights', 'best.pt')
    if os.path.exists(best_weights):
        # Deploy directly to server model directory for production runtime
        deploy_dir = "server/models"
        os.makedirs(deploy_dir, exist_ok=True)
        deployed_path = os.path.join(deploy_dir, "hazard_yolo11.pt")
        shutil.copy2(best_weights, deployed_path)
        logger.info(f"✅ Successfully deployed trained weights to {deployed_path}")
        return deployed_path
    else:
        logger.warning("best.pt not found in runs folder.")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train VisionAid Hazard Detection Model")
    parser.add_argument('--epochs', type=int, default=15, help="Number of training epochs")
    parser.add_argument('--batch', type=int, default=16, help="Batch size")
    parser.add_argument('--device', type=str, default="cpu", help="Compute device ('cpu' or GPU index '0')")
    parser.add_argument('--data', type=str, default="training/datasets/accessibility_hazards/data.yaml", help="Dataset YAML")
    parser.add_argument('--base', type=str, default="yolo11n.pt", help="Pretrained base model weights")
    args = parser.parse_args()

    train_hazard_detector(
        data_yaml=args.data,
        base_model=args.base,
        epochs=args.epochs,
        batch_size=args.batch,
        device=args.device
    )
