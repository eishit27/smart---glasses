# VisionAid — Heavy Model Training & Accessibility Fine-Tuning Guide

This guide details how we train, fine-tune, and optimize computer vision and AI models specifically for **visually impaired pedestrian navigation**.

---

## 1. Why Generic Models Fail (The Problem)

Generic models trained on the standard COCO dataset (like stock YOLO) detect *surfboards, teddy bears, giraffes, toasters, and baseball bats*. They were built for general consumer apps, not accessibility.

For a blind person, the most critical physical dangers are:
1. **Falling down stairs** (#1 indoor/outdoor fall hazard)
2. **Stepping off a curb into traffic**
3. **Head-level collisions** (low tree branches, awnings, scaffolding) — *white canes only detect ground level!*
4. **Transparent glass doors and walls**
5. **Thin poles and bollards**

---

## 2. Our Custom Accessibility Dataset & Classes

We replace generic 80-class COCO detection with **11 specialized accessibility classes**:

| Class ID | Name | Life-Safety Purpose |
|---|---|---|
| `0` | **`stairs_up`** | Ascending staircase detection; locate first step |
| `1` | **`stairs_down`** | Descending staircase warning (Immediate fall prevention) |
| `2` | **`curb`** | Sidewalk edge; transition into road or vehicular path |
| `3` | **`head_hazard`** | Low branches, awnings, construction pipes at eye/head height |
| `4` | **`ground_obstacle`** | Potholes, tripping wires, puddles, open trenches |
| `5` | **`pole_bollard`** | Thin vertical posts that blend into street background |
| `6` | **`glass_door`** | Transparent sliding doors, glass storefront partitions |
| `7` | **`crosswalk`** | Striped zebra pedestrian crossings |
| `8` | **`pedestrian_signal`** | Red ("Don't Walk") vs. Green/White ("Walk") indicators |
| `9` | **`vehicle`** | Approaching cars, motorcycles, bicycles, buses |
| `10` | **`person`** | Pedestrians, crowds |

---

## 3. Training Options

### Option A: Local Pipeline Execution
To generate the dataset and launch local transfer learning:

```bash
# Automated 1-step pipeline:
bash training/run_training_pipeline.sh 20 16 cpu
```

Or step-by-step:
```bash
# 1. Generate/Augment Dataset
python3 training/dataset_builder.py

# 2. Train Custom YOLO11
python3 training/train_yolo_hazards.py --epochs 25 --batch 16 --device cpu

# 3. Export to Edge Hardware (OpenVINO / ONNX)
python3 training/export_edge.py --weights server/models/hazard_yolo11.pt --format onnx
```

### Option B: Heavy GPU Training on Google Colab (Recommended for Large Batches)
Your laptop runs on an Intel Core i7 CPU. For **heavy training** on 10,000+ real-world images at 100 epochs, run on a **free cloud NVIDIA GPU (T4 / A100)**:

1. Open [`training/VisionAid_Google_Colab_GPU_Training.ipynb`](../training/VisionAid_Google_Colab_GPU_Training.ipynb) in **[Google Colab](https://colab.research.google.com)**.
2. Select **Runtime → Change runtime type → T4 GPU**.
3. Run all cells to train at maximum speed (~15 minutes for 100 epochs).
4. Download the generated `best.pt` file and save it to `server/models/hazard_yolo11.pt`.
5. The VisionAid server will **automatically detect and activate** the custom model on the next launch!

---

## 4. Key Engineering Innovations in Our Pipeline

### 📐 1. Metric Depth Calibration (`server/vision/metric_depth.py`)
Monocular depth estimation models produce *relative disparity* (unitless 0 to 1). We solve this mathematically by using:
- Physical eye-level mounting height ($H \approx 1.65\text{m}$)
- Optical ray-tracing against the forward ground plane: $Z = \frac{H}{\tan(\text{pitch} + \phi_y)}$
- Dynamically scales inverse relative depth to **real physical meters** (e.g., *"Curb 1.2 meters ahead"*).

### 🔊 2. Sub-30ms Directional Audio Earcons (`server/audio/earcons.py`)
Speaking a full sentence takes 2 to 3 seconds. At a normal walking speed of 1.4 m/s, the user would walk 3.5 meters before TTS finishes speaking.
- **Our solution**: For immediate hazards (<1.2m), the glasses play a **stereo-panned acoustic tick** (<30ms latency).
- Closer obstacles = higher urgent frequency. Left vs. right = stereo panning.

### 🛑 3. Tracking & De-Bouncing Filter (`server/vision/tracker.py`)
Treating every frame independently causes alert fatigue (shouting *"chair ahead"* every single second).
- Tracks obstacles across frames via IoU.
- Computes **Approach Velocity** and **Time-to-Collision (TTC)**.
- Only fires alerts when a new obstacle enters the path or is actively closing distance.
