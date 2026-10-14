# VisionAid Firmware

This directory contains the PlatformIO project for the VisionAid Smart Glasses.
The firmware is designed for the **Seeed XIAO ESP32S3 Sense**.

## Setup

1. Install [PlatformIO](https://platformio.org/).
2. Open the `firmware/` directory in VSCode/PlatformIO.
3. The board is pre-configured in `platformio.ini` as `seeed_xiao_esp32s3`.

## Pin Connections

| ESP32 Pin | Component |
| --- | --- |
| D0 / GPIO0 | User Button (BOOT) |
| D5 | Haptic Motor |
| D21 | Privacy LED |
| A4 | Ambient Light Sensor (LDR) |

*(Camera pins are internally wired on the XIAO Sense board).*

## Flashing

Run the `Upload` command in PlatformIO.
If the board is not detected, put it in bootloader mode by holding the BOOT button while plugging in the USB, or double-pressing RESET.

## Debugging

Run the `Monitor` task in PlatformIO to view serial logs at `115200` baud.
Note: To view crash decodes, ensure `monitor_filters = esp32_exception_decoder` is added to `platformio.ini`.
