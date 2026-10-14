#include "haptic.h"
#include <Arduino.h>

#define HAPTIC_PIN 5 // Example pin for haptic motor

struct PatternStep {
    uint8_t intensity; // 0-255 PWM
    uint16_t durationMs;
};

// Define patterns
static const PatternStep pulsePattern[] = {{255, 100}, {0, 0}};
static const PatternStep continuousPattern[] = {{150, 60000}, {0, 0}};
static const PatternStep sosPattern[] = {
    {255, 200}, {0, 100}, {255, 200}, {0, 100}, {255, 200}, {0, 300},
    {255, 600}, {0, 100}, {255, 600}, {0, 100}, {255, 600}, {0, 300},
    {255, 200}, {0, 100}, {255, 200}, {0, 100}, {255, 200}, {0, 0}
};
static const PatternStep warningPattern[] = {{255, 500}, {0, 200}, {255, 500}, {0, 0}};

static const PatternStep* currentPattern = nullptr;
static uint8_t currentStep = 0;
static unsigned long stepStartTime = 0;
static unsigned long patternMaxDuration = 0;
static unsigned long patternStartTime = 0;

void Haptic::init() {
    pinMode(HAPTIC_PIN, OUTPUT);
    digitalWrite(HAPTIC_PIN, LOW);
    // Alternatively set up ledc for PWM
}

void Haptic::playPattern(HapticPattern pattern, unsigned long durationMs) {
    switch (pattern) {
        case HAPTIC_PATTERN_PULSE: currentPattern = pulsePattern; break;
        case HAPTIC_PATTERN_CONTINUOUS: currentPattern = continuousPattern; break;
        case HAPTIC_PATTERN_SOS: currentPattern = sosPattern; break;
        case HAPTIC_PATTERN_WARNING: currentPattern = warningPattern; break;
    }
    currentStep = 0;
    stepStartTime = millis();
    patternStartTime = millis();
    patternMaxDuration = durationMs;
    
    // Apply first step
    analogWrite(HAPTIC_PIN, currentPattern[currentStep].intensity);
}

void Haptic::stop() {
    currentPattern = nullptr;
    analogWrite(HAPTIC_PIN, 0);
}

void Haptic::update() {
    if (!currentPattern) return;
    
    unsigned long now = millis();
    
    // Check max duration limit
    if (patternMaxDuration > 0 && (now - patternStartTime >= patternMaxDuration)) {
        stop();
        return;
    }
    
    // Check step duration
    if (now - stepStartTime >= currentPattern[currentStep].durationMs) {
        currentStep++;
        
        // End of pattern indicator (duration 0)
        if (currentPattern[currentStep].durationMs == 0) {
            stop();
        } else {
            stepStartTime = now;
            analogWrite(HAPTIC_PIN, currentPattern[currentStep].intensity);
        }
    }
}
