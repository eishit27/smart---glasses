#include "button.h"
#include <Arduino.h>

#define BUTTON_PIN 0 // BOOT button often used, or touch pin

static unsigned long lastDebounceTime = 0;
static const unsigned long debounceDelay = 50;
static int buttonState = HIGH;
static int lastButtonState = HIGH;

static unsigned long pressStartTime = 0;
static uint8_t pressCount = 0;
static unsigned long lastReleaseTime = 0;
static const unsigned long multiClickThreshold = 400; // ms
static const unsigned long longPressThreshold = 1000; // ms

void Button::init() {
    pinMode(BUTTON_PIN, INPUT_PULLUP);
}

ButtonEvent Button::process() {
    int reading = digitalRead(BUTTON_PIN);
    ButtonEvent event = EVENT_NONE;

    if (reading != lastButtonState) {
        lastDebounceTime = millis();
    }

    if ((millis() - lastDebounceTime) > debounceDelay) {
        if (reading != buttonState) {
            buttonState = reading;

            if (buttonState == LOW) {
                // Button Pressed
                pressStartTime = millis();
            } else {
                // Button Released
                unsigned long pressDuration = millis() - pressStartTime;
                if (pressDuration > longPressThreshold) {
                    event = EVENT_LONG_PRESS;
                    pressCount = 0; // reset
                } else {
                    pressCount++;
                    lastReleaseTime = millis();
                }
            }
        }
    }
    
    // Evaluate multi-clicks after threshold passes
    if (pressCount > 0 && buttonState == HIGH && (millis() - lastReleaseTime) > multiClickThreshold) {
        if (pressCount == 1) event = EVENT_SINGLE_PRESS;
        else if (pressCount == 2) event = EVENT_DOUBLE_PRESS;
        else if (pressCount >= 3) event = EVENT_TRIPLE_PRESS;
        
        pressCount = 0; // reset
    }

    lastButtonState = reading;
    return event;
}
