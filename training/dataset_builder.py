"""
VisionAid Accessibility Hazard Dataset Builder
==============================================

Builds and packages training datasets tailored specifically to the real-world
hazards faced by blind and visually impaired pedestrians.

Uses standard Python libraries (PIL, numpy, yaml) to ensure 100% offline compatibility.

Classes:
  0: stairs_up
  1: stairs_down
  2: curb
  3: head_hazard       (branches, scaffolding, awnings at head height)
  4: ground_obstacle   (potholes, tripping wires, puddles, trenches)
  5: pole_bollard      (thin poles, street signs, bollards)
  6: glass_door        (transparent doors, glass walls)
  7: crosswalk         (zebra crossings)
  8: pedestrian_signal (walk / do not walk lights)
  9: vehicle           (cars, bikes, buses)
 10: person            (pedestrians)
"""

import os
import yaml
import random
import logging
from typing import Tuple, List
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HAZARD_CLASSES = [
    "stairs_up",
    "stairs_down",
    "curb",
    "head_hazard",
    "ground_obstacle",
    "pole_bollard",
    "glass_door",
    "crosswalk",
    "pedestrian_signal",
    "vehicle",
    "person"
]

class AccessibilityDatasetBuilder:
    def __init__(self, output_dir: str = "training/datasets/accessibility_hazards"):
        self.output_dir = output_dir
        self.img_w = 640
        self.img_h = 640
        
        for split in ['train', 'val', 'test']:
            os.makedirs(os.path.join(self.output_dir, "images", split), exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, "labels", split), exist_ok=True)

    def generate_data_yaml(self) -> str:
        """Creates standard YOLO data.yaml configuration."""
        yaml_path = os.path.join(self.output_dir, "data.yaml")
        abs_output_dir = os.path.abspath(self.output_dir)
        
        data = {
            'path': abs_output_dir,
            'train': 'images/train',
            'val': 'images/val',
            'test': 'images/test',
            'names': {i: name for i, name in enumerate(HAZARD_CLASSES)}
        }
        
        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, sort_keys=False)
            
        logger.info(f"Generated dataset YAML configuration at {yaml_path}")
        return yaml_path

    def generate_synthetic_hazard_frame(self) -> Tuple[Image.Image, List[Tuple[int, float, float, float, float]]]:
        """
        Creates a synthetic ground-perspective hazard scene with accurate bounding boxes using PIL.
        """
        # Background sky/wall
        bg_color = (random.randint(180, 220), random.randint(190, 225), random.randint(200, 230))
        img = Image.new("RGB", (self.img_w, self.img_h), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Ground plane (lower 55%)
        horizon_y = int(self.img_h * 0.45)
        ground_color = (random.randint(90, 130), random.randint(90, 130), random.randint(90, 130))
        draw.rectangle([0, horizon_y, self.img_w, self.img_h], fill=ground_color)

        annotations = [] # [class_id, x_center, y_center, width, height]

        hazard_types = [
            (0, "stairs_up"),
            (1, "stairs_down"),
            (2, "curb"),
            (3, "head_hazard"),
            (4, "ground_obstacle"),
            (5, "pole_bollard"),
            (6, "glass_door"),
            (7, "crosswalk")
        ]

        selected = random.sample(hazard_types, k=random.randint(1, 3))

        for cls_id, name in selected:
            if name == "stairs_down":
                # Descending stairs near bottom of screen
                x1, y1 = random.randint(50, 150), int(self.img_h * 0.65)
                x2, y2 = random.randint(450, 580), self.img_h - 10
                for step_y in range(y1, y2, 22):
                    draw.line([(x1, step_y), (x2, step_y)], fill=(30, 30, 30), width=4)

            elif name == "stairs_up":
                # Ascending stairs
                x1, y1 = random.randint(150, 250), int(self.img_h * 0.40)
                x2, y2 = random.randint(380, 500), int(self.img_h * 0.75)
                draw.rectangle([x1, y1, x2, y2], fill=(60, 60, 60))

            elif name == "head_hazard":
                # Overhanging branch or scaffolding
                x1, y1 = random.randint(100, 300), 0
                x2, y2 = x1 + random.randint(150, 250), random.randint(120, 220)
                draw.rectangle([x1, y1, x2, y2], fill=(45, 75, 35))

            elif name == "pole_bollard":
                # Thin bollard
                x1 = random.randint(100, 500)
                y1 = int(self.img_h * 0.45)
                x2 = x1 + random.randint(20, 45)
                y2 = int(self.img_h * 0.85)
                draw.rectangle([x1, y1, x2, y2], fill=(180, 30, 30))

            elif name == "curb":
                # Curb line
                x1, y1 = 0, int(self.img_h * 0.70)
                x2, y2 = self.img_w, int(self.img_h * 0.78)
                draw.rectangle([x1, y1, x2, y2], fill=(160, 160, 160))

            elif name == "crosswalk":
                # Zebra stripes
                x1, y1 = random.randint(50, 100), int(self.img_h * 0.60)
                x2, y2 = random.randint(500, 600), int(self.img_h * 0.95)
                for stripe_x in range(x1, x2, 50):
                    draw.rectangle([stripe_x, y1, stripe_x + 25, y2], fill=(255, 255, 255))

            elif name == "glass_door":
                # Glass door with outline
                x1, y1 = random.randint(100, 200), int(self.img_h * 0.20)
                x2, y2 = random.randint(400, 550), int(self.img_h * 0.85)
                draw.rectangle([x1, y1, x2, y2], outline=(220, 230, 245), width=3)
                draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255), width=2)

            else: # ground obstacle
                x1, y1 = random.randint(180, 350), int(self.img_h * 0.65)
                x2, y2 = x1 + random.randint(60, 140), y1 + random.randint(40, 90)
                draw.ellipse([x1, y1, x2, y2], fill=(20, 20, 20))

            # YOLO format
            bw = (x2 - x1) / self.img_w
            bh = (y2 - y1) / self.img_h
            bx = (x1 + x2) / (2.0 * self.img_w)
            by = (y1 + y2) / (2.0 * self.img_h)
            annotations.append((cls_id, bx, by, bw, bh))

        # Augmentations (walking motion blur & lighting)
        if random.random() > 0.3:
            img = img.filter(ImageFilter.GaussianBlur(radius=random.choice([1, 2])))
        if random.random() > 0.4:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(random.uniform(0.7, 1.3))

        return img, annotations

    def build_dataset(self, num_train: int = 150, num_val: int = 30, num_test: int = 20):
        """Builds complete partitioned dataset."""
        logger.info(f"Generating Accessibility Hazard Dataset: {num_train} train, {num_val} val, {num_test} test...")
        
        splits = [
            ('train', num_train),
            ('val', num_val),
            ('test', num_test)
        ]
        
        for split, count in splits:
            for i in range(count):
                img, annos = self.generate_synthetic_hazard_frame()
                img_name = f"hazard_{split}_{i:04d}.jpg"
                txt_name = f"hazard_{split}_{i:04d}.txt"
                
                img_path = os.path.join(self.output_dir, "images", split, img_name)
                txt_path = os.path.join(self.output_dir, "labels", split, txt_name)
                
                img.save(img_path, quality=90)
                
                with open(txt_path, 'w') as f:
                    for cls_id, bx, by, bw, bh in annos:
                        f.write(f"{cls_id} {bx:.6f} {by:.6f} {bw:.6f} {bh:.6f}\n")
                        
        self.generate_data_yaml()
        logger.info(f"✅ Accessibility Hazard Dataset successfully created in {self.output_dir}")

if __name__ == "__main__":
    builder = AccessibilityDatasetBuilder()
    builder.build_dataset(num_train=120, num_val=24, num_test=12)
