/**
 * VisionAid Smart Glasses - Firmware Main Entry Point
 * 
 * This is an assistive device firmware. Reliability is key.
 * 
 * Responsibilities:
 * - Initialize camera, BLE, haptic, button, privacy LED
 * - Main loop: capture frame → send via BLE → check button → handle commands
 * - Power management: deep sleep when idle
 */
#include <Arduino.h>
#include "camera.h"
#include "ble_comm.h"
#include "haptic.h"
#include "button.h"
#include "privacy.h"

// State machine
enum DeviceState {
    STATE_IDLE,
    STATE_STREAMING,
    STATE_ON_DEMAND
};

DeviceState currentState = STATE_IDLE;
unsigned long lastActionTime = 0;
const unsigned long IDLE_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes to deep sleep

void setup() {
    // Thermal & Battery Optimization: Scale clock from 240MHz down to 160MHz
    // Cuts thermal heat dissipation by ~40% while maintaining full camera speed
    setCpuFrequencyMhz(160);

    Serial.begin(115200);
    Serial.println("Starting VisionAid Firmware (Cool & Power-Optimized)...");
    
    // Privacy LED interlock MUST be initialized first for safety compliance
    Privacy::init();
    
    // Initialize user IO
    Button::init();
    Haptic::init();
    
    // Play startup sequence
    Haptic::playPattern(HAPTIC_PATTERN_PULSE);
    
    // Initialize Camera
    if (!Camera::init()) {
        Serial.println("Camera initialization failed! Halting.");
        Haptic::playPattern(HAPTIC_PATTERN_SOS);
        while (1) { delay(100); } // Watchdog will eventually reset if enabled
    }
    
    // Initialize BLE
    BLEComm::init();
    
    lastActionTime = millis();
    Serial.println("Initialization complete.");
}

void loop() {
    // 1. Process Input
    ButtonEvent event = Button::process();
    if (event != EVENT_NONE) {
        lastActionTime = millis();
        // Forward button event over BLE
        BLEComm::sendCommand((uint8_t)event);
        
        switch (event) {
            case EVENT_SINGLE_PRESS:
                // Scan scene (on-demand)
                currentState = STATE_ON_DEMAND;
                Haptic::playPattern(HAPTIC_PATTERN_PULSE);
                break;
            case EVENT_LONG_PRESS:
                // Toggle streaming mode
                if (currentState == STATE_STREAMING) {
                    currentState = STATE_IDLE;
                    Haptic::playPattern(HAPTIC_PATTERN_PULSE); // Stopped
                } else {
                    currentState = STATE_STREAMING;
                    Haptic::playPattern(HAPTIC_PATTERN_CONTINUOUS, 500); // Started
                }
                break;
            // Handle double, triple as needed
            default:
                break;
        }
    }
    
    // 2. Process BLE incoming commands
    BLEComm::process();
    
    // 3. Handle State
    if (currentState == STATE_STREAMING || currentState == STATE_ON_DEMAND) {
        // Enforce privacy before capture
        if (Privacy::isCovered()) {
            Serial.println("Privacy violation detected! Camera operation blocked.");
            Haptic::playPattern(HAPTIC_PATTERN_WARNING);
            currentState = STATE_IDLE; // Force idle
        } else {
            Privacy::setLed(true);
            
            camera_fb_t * fb = Camera::capture();
            if (fb) {
                BLEComm::sendFrame(fb->buf, fb->len);
                Camera::release(fb);
                
                if (currentState == STATE_ON_DEMAND) {
                    currentState = STATE_IDLE; // Capture once and go back to idle
                }
            } else {
                Serial.println("Camera capture failed!");
            }
            
            if (currentState == STATE_IDLE) {
                Privacy::setLed(false); // Turn off if going to idle
            }
        }
        lastActionTime = millis();
    } else {
        Privacy::setLed(false);
    }
    
    // 4. Update async peripherals
    Haptic::update();
    
    // 5. Power Management
    if (millis() - lastActionTime > IDLE_TIMEOUT_MS) {
        Serial.println("Idle timeout. Entering deep sleep...");
        Haptic::playPattern(HAPTIC_PATTERN_PULSE);
        delay(500); // Wait for haptic
        // Configure wake up source (e.g., ext0 on button pin)
        // esp_sleep_enable_ext0_wakeup(BUTTON_PIN, 0); 
        esp_deep_sleep_start();
    }
    
    delay(10); // Yield to RTOS
}
