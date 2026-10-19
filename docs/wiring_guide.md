# VisionAid Smart Glasses — Complete Wiring & Assembly Guide

This document is the step-by-step physical assembly, soldering, and wiring blueprint for the VisionAid Smart Glasses.

---

## ⚡ 1. System Pinout & Electrical Interconnect

### Seeed Studio XIAO ESP32-S3 Sense Pinout

| Pin / Pad | GPIO | Function | Connects To | Temple Side |
|---|---|---|---|---|
| **BAT+** | VBAT | LiPo 3.7V Battery In | TP4056 `OUT+` (via browline red wire) | Left ↔ Right |
| **GND** | GND | Common Ground | TP4056 `OUT-` / All modules GND | Left ↔ Right |
| **3V3** | 3.3V | 3.3V Regulated Output | BMI270 `VCC` / MAX98306 `VDD` | Left |
| **D0** | GPIO 1 | Button 1 Input (Scan) | Right Temple Button 1 (to GND) | Left ↔ Right |
| **D1** | GPIO 2 | Button 2 Input (OCR) | Right Temple Button 2 (to GND) | Left ↔ Right |
| **D2** | GPIO 3 | Audio Out / PWM DAC | MAX98306 `IN+` (Class-D Amp) | Left |
| **D3** | GPIO 4 | I²C SDA | BMI270 IMU `SDA` | Left |
| **D4** | GPIO 5 | I²C SCL | BMI270 IMU `SCL` | Left |
| **D5** | GPIO 6 | Haptic Motor PWM | 10mm Coin Haptic (+) via 2N2222 / direct | Left |
| **D6** | GPIO 21 | Privacy LED Interlock | White 2.8mm SMD LED Anode (via 100Ω) | Left ↔ Front |
| **FPC Port**| MIPI/DVP | Camera Ribbon Port | OV5640 5MP Autofocus Flex Cable | Left ↔ Front |

---

## 🕶️ 2. Subsystem Wiring Schematics

### A. Right Temple: Power, Charging & Controls
```
               ┌────────────────────────────────────────────────────────┐
               │                  RIGHT TEMPLE ARM                      │
               │                                                        │
[USB-C Cable]  │                                                        │
      │        │  ┌──────────────┐     B+      ┌──────────────────────┐ │
      └───────►│  │   TP4056     ├────────────►│ 800mAh 3.7V LiPo     │ │
 [Bottom Port] │  │ USB-C Board  │             │ Battery (w/ PCM)     │ │
               │  │              ├────────────►│                      │ │
               │  └──────┬──┬────┘     B-      └──────────────────────┘ │
               │     OUT+│  │OUT-                                       │
               │         │  │                                           │
               │         │  └──────────────────────────────────────┐    │
               │         │                                         │    │
               │  ┌──────┴────────┐                    ┌───────────┴──┐ │
               │  │ Tactile Btn 1 │                    │Tactile Btn 2 │ │
               │  │ (Scene Scan)  │                    │(Read OCR)    │ │
               │  └──────┬────────┘                    └───────┬──────┘ │
               │         │ Sig 1                               │ Sig 2  │
               └─────────┼─────────────────────────────────────┼────────┘
                         │                                     │
           ================ BROWLINE CONDUIT ==================
            4-5x Thin 30AWG Silicone Wires Through Top Bar
           ====================================================
                         │                                     │
               ┌─────────┼─────────────────────────────────────┼────────┐
               │         ▼                                     ▼        │
               │      BAT+ / GND                             D0 / D1    │
               │                                                        │
               │                  LEFT TEMPLE ARM                       │
               │          (Seeed XIAO ESP32-S3 Sense Brain)             │
               └────────────────────────────────────────────────────────┘
```

### B. Left Temple: Compute, Vision & Audio
```
┌─────────────────────────────────────────────────────────────────────────┐
│                           LEFT TEMPLE ARM                               │
│                                                                         │
│   ┌──────────────────────────────────────────────┐                      │
│   │        Seeed XIAO ESP32-S3 Sense             │                      │
│   │                                              │                      │
│   │  [FPC Ribbon Port] ──► OV5640 5MP Camera     │ (Front Left Corner)  │
│   │  GPIO 21 ────────────► Privacy LED (w/ 100Ω) │ (Front Next to Cam)  │
│   │                                              │                      │
│   │  3V3 / GND ──────────► BMI270 6-Axis IMU     │ (Bay 1 Floor)        │
│   │  SDA (D3) / SCL (D4) ─►                      │                      │
│   │                                              │                      │
│   │  GPIO 6 (D5) ────────► 10mm Coin Haptic      │ (Bay 3 Pocket)       │
│   │                                              │                      │
│   │  3V3 / GND ──────────┐                       │                      │
│   │  Audio Out (D2) ─────┴► MAX98306 Class-D Amp │ (Stacked Bay 1)      │
│   │                           │          │       │                      │
│   └───────────────────────────┼──────────┼───────┘                      │
│                               │ L+ / L-  │ R+ / R- (via browline)       │
│                               ▼          ▼                              │
│                      [Left Bone Conductor]  [Right Bone Conductor]      │
│                      (Left Cheek Swell)     (Right Cheek Swell)         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🧵 3. Browline Interconnect (Crossing the Bridge)

To connect the Right Temple (Power + Buttons) to the Left Temple (Brain), route **4 thin 30AWG ultra-flexible silicone wires** through the browline channel of the front frame:

1. **Wire 1 (Red)**: `VCC` (+3.7V from TP4056 `OUT+` to XIAO `BAT+`)
2. **Wire 2 (Black)**: `GND` (Common ground from TP4056 `OUT-` to XIAO `GND`)
3. **Wire 3 (Yellow)**: `BTN_SCAN` (Button 1 signal to XIAO `D0`)
4. **Wire 4 (Blue)**: `AUDIO_R+` (Right audio channel from MAX98306 to Right Transducer)

*(Tip: Both buttons can share the common GND wire in the right temple arm).*

---

## 🛠️ 4. Step-by-Step Soldering & Assembly Order

### Phase 1: Pre-Wiring the Components on the Bench
1. **Camera Module**: Gently lift the FPC locking collar on the XIAO Sense board, insert the OV5640 ribbon cable with gold contacts facing down, and push the collar closed.
2. **TP4056 & Battery**:
   - Solder the battery Red wire to `B+` and Black wire to `B-` on the TP4056 board.
   - Solder two 30AWG leads (Red/Black) to `OUT+` and `OUT-`.
3. **MAX98306 Amplifier**:
   - Connect `VDD` to 3.3V and `GND` to Ground.
   - Connect `IN+` to XIAO `D2` (Audio DAC/PWM) and `IN-` to Analog Ground.
   - Attach Left Transducer leads to `L_OUT+` and `L_OUT-`.
4. **Privacy LED**: Solder the 100Ω SMD resistor directly to the anode (+) leg of the 2.8mm white LED, wrap in 1.5mm heat-shrink, and wire to GPIO 21.

### Phase 2: Installing Into the 3D Printed Frame
1. **Front Frame**:
   - Press-fit the OV5640 camera lens into the front-left corner aperture (8.7mm bore).
   - Press-fit the 2.8mm privacy LED into the adjacent aperture.
   - Feed the 4 browline wires through the top frame channel from right to left.
2. **Left Temple Chassis**:
   - Seat the XIAO ESP32-S3 Sense into Bay 1 on the support shelves.
   - Place the BMI270 IMU underneath/beside the board.
   - Press the Left Bone Conduction transducer into Bay 2 with acoustic face contacting the cheek swell.
   - Press the 10mm coin haptic motor into the circular Bay 3 pocket (use the 3M adhesive backing).
3. **Right Temple Chassis**:
   - Place the 800mAh LiPo battery into Bay 1.
   - Fit the 2 tactile buttons into the top rail guide ports so the plungers protrude through the top edge.
   - Press the Right Bone Conduction transducer into Bay 2.
   - Place the TP4056 charger into Bay 3, aligning the USB-C port with the bottom rail cutout.

---

## 🔍 5. Pre-Power Safety Checklist (Multimeter Verification)

> [!CAUTION]
> **Always perform these tests BEFORE connecting the battery or plugging in USB-C:**
>
> 1. **Continuity & Short-Circuit Check**: Set multimeter to continuity/beep mode. Touch probes to `VCC` and `GND`. **There MUST be NO beep.** If it beeps, find and eliminate the short circuit immediately.
> 2. **Polarity Check**: Verify that Red wire is strictly +3.7V/VCC and Black wire is Ground at every board pad. Reverse polarity will instantly destroy the ESP32 chip.
> 3. **Hinge Free Movement**: Fold both temple arms back and forth to ensure the silicone wires inside the hinge knuckles do not pinch or bind against the hinge screws.

---

## 🔒 6. Final Lid Sealing

1. Slide the 4 retention tabs of the **Left Lid** into the top and bottom rail slots.
2. Fasten the 2× **M1.4/M1.6 × 4mm screws** into Boss 1 (u=38mm) and Boss 2 (u=82mm).
3. Repeat for the **Right Lid** (screws at u=53mm and u=94mm).
4. The glasses are now 100% sealed, sweat-resistant, and ready for power-on!
