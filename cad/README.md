# VisionAid Smart Glasses — 3D CAD & Manufacturing Guide

This directory contains the production-grade 3D CAD files for the VisionAid Smart Glasses frame, ready to send to any commercial 3D printing service or slice on a desktop 3D printer.

---

## 🕶️ Design Architecture: Ray-Ban Meta / Bose Frames Style

- **100% Clean Designer Front Frame**: **Zero center box** on the browline or nose bridge. Features a classic Wayfarer shape with an open keyhole/saddle arch and comfortable resting nose pads.
- **Discreet Corner Camera**: The OV5640 autofocus camera sits in the front-left browline end piece (looking like a stylish designer rivet) with a privacy LED right next to it.
- **Enlarged Smart Temples**: Both temple arms are thickened (18–21.5mm height, 7.2mm thickness tapering to 6.5mm) to house all electronics cleanly inside the arms:
  - **Left Temple**: Seeed Studio XIAO ESP32-S3 Sense + camera ribbon channel + left bone-conduction transducer + 10mm haptic motor.
  - **Right Temple**: 450mAh LiPo battery + TP4056 USB-C charging module + right bone-conduction transducer + dual click buttons.
- **Balanced Weight Distribution**: ~13g on the left arm and ~13g on the right arm creates perfect counter-balance with **zero weight dragging down the nose bridge**.

---

## 📦 What Files Are Included?

### 1. Master Assembled 3D Preview (`cad/stl/`)
Drop this single file into any 3D viewer (such as [ViewSTL.com](https://www.viewstl.com/), Windows 3D Viewer, or Blender) to inspect the complete glasses:

* [`visionaid_assembled_glasses.stl`](stl/visionaid_assembled_glasses.stl) — Full glasses assembly in true 3D perspective with front frame and both smart temples extending backwards.

### 2. Ready-to-Print Binary STL Files (`cad/stl/`)
Upload these individual files to your 3D printing service or slicer:

| File | Component | What Fits Inside / Exact Cavity |
|---|---|---|
| [`1_front_frame.stl`](stl/1_front_frame.stl) | Designer Front Chassis | 144mm width, dual 49×40mm rims, open keyhole bridge, resting nose pads, and 8.7mm front-left corner camera port. |
| [`2_left_temple_arm.stl`](stl/2_left_temple_arm.stl) | Left Smart Temple Arm | **Seeed XIAO ESP32-S3** cavity (24×18.5×5.4mm), camera ribbon channel, **bone-conduction pad** (15.5×14.5×5mm), and **10mm haptic motor** pocket. |
| [`3_right_temple_arm.stl`](stl/3_right_temple_arm.stl) | Right Smart Temple Arm | **450mAh LiPo battery** cavity (38×19×5.4mm), **TP4056 USB-C charger** cavity (30×15×5mm), bottom USB-C slot (9.5×3.6mm), top dual button ports, and right bone-conduction pad. |
| [`4_left_temple_lid.stl`](stl/4_left_temple_lid.stl) | Left Inner Cover Lid | 0.8mm smooth snap-fit cover plate that seals the left electronics compartment flush against hair/skin. |
| [`5_right_temple_lid.stl`](stl/5_right_temple_lid.stl) | Right Inner Cover Lid | 0.8mm smooth snap-fit cover plate that seals the right battery compartment flush against hair/skin. |

*(Note: Legacy file names `front_frame.stl`, `left_temple_arm.stl`, etc. are also preserved in `cad/stl/` for automated tool compatibility).*

### 3. Parametric OpenSCAD Source (`cad/openscad/`)
* [`visionaid_complete_assembly.scad`](openscad/visionaid_complete_assembly.scad): Fully parametric OpenSCAD master model.

### 4. Automated STL Generator Script (`cad/scripts/`)
* [`generate_stl.py`](scripts/generate_stl.py): Standalone Python script that generates all watertight binary `.stl` meshes mathematically using numpy. Run with `python3 cad/scripts/generate_stl.py`.

---

## 📐 Component Dimensional Specifications & Clearances

| Component | Physical Size (L × W × H) | CAD Cavity Provided | Clearances & Tolerances |
|---|---|---|---|
| **Seeed XIAO ESP32-S3 Sense** | 21.0 × 17.5 × 4.2 mm | 24.0 × 18.5 × 5.4 mm | +3.0mm length, +1.0mm height, +1.2mm depth for wiring and solder joints. |
| **OV5640 Auto-Focus Camera** | 8.5 × 8.5 × 5.2 mm | 8.7mm dia bezel + 14mm ribbon conduit | Flush bezel mount in front-left corner with 0.2mm press-fit tolerance. |
| **450mAh 1S LiPo Battery (502035)** | 35.0 × 20.0 × 5.0 mm | 38.0 × 19.0 × 5.4 mm | +3.0mm length for battery protection circuit and soft-expansion cushion. |
| **TP4056 / Micro USB-C Charger** | 28.0 × 17.0 × 4.0 mm | 30.0 × 15.0 × 5.0 mm | Dedicated bottom-edge 9.5 × 3.6 mm USB-C port cutout. |
| **Bone Conduction Transducers (Pair)** | 14.0 × 14.0 × 4.5 mm | 15.5 × 14.5 × 5.0 mm | Built into 3.2mm inward-protruding zygomatic bone contact pads on each arm. |
| **Coin Haptic Vibration Motor** | 10.0 mm dia × 3.0 mm | 12.0 × 12.0 × 3.2 mm | Snug vibration pocket in left arm for haptic obstacle pulses. |

---

## 🏭 Recommended 3D Printing Material

| Printing Method | Recommended Material | Quality & Durability | Recommended For |
|---|---|---|---|
| **SLS (Selective Laser Sintering)** ⭐ *Top Pick* | **Nylon PA12 (Matte Black)** | **Commercial Grade**. No layer lines, skin-hypoallergenic, flexible, unbreakable. Matches commercial eyewear. | Professional fabrication (JLC3DP, Robu.in). |
| **SLA (Resin)** | **Tough / ABS-Like Resin** | **Ultra-Smooth finish**. Crisp edges for snap-fit lids and button holes. | High-detail prototyping. |
| **FDM (Desktop 3D Printer)** | **PETG or PLA+** | **Budget option**. Print arms flat on outer face with 0.16mm layer height and tree supports. | Home DIY printing. |

---

## 🔩 Assembly & Fasteners

1. **Hinge Screws**: 2× standard **M1.6 × 6mm** (or M1.4 eyeglass) stainless steel screws with nuts.
2. **Wiring**: A thin 2-wire micro-enamel wire pair (30 AWG) routes power from the right temple battery along the internal frame browline groove to the left temple compute board.
3. **Sealing**: Snap-fit inner lids (`4_left_temple_lid.stl` and `5_right_temple_lid.stl`) lock into place with micro retention tabs.
