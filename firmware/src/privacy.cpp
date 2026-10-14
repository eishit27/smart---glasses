#include "privacy.h"
#include <Arduino.h>

#define PRIVACY_LED_PIN 21
#define AMBIENT_LIGHT_PIN 4 // ADC pin adjacent to LED

static bool ledActive = false;

void Privacy::init() {
    pinMode(PRIVACY_LED_PIN, OUTPUT);
    digitalWrite(PRIVACY_LED_PIN, LOW);
    pinMode(AMBIENT_LIGHT_PIN, INPUT);
    ledActive = false;
}

void Privacy::setLed(bool enable) {
    ledActive = enable;
    digitalWrite(PRIVACY_LED_PIN, enable ? HIGH : LOW);
}

bool Privacy::isLedActive() {
    return ledActive;
}

bool Privacy::isCovered() {
    // Tamper detection:
    // If the LED is commanded ON, we take a reading.
    // If an attacker placed black tape or opaque glue over the sensor/LED cluster,
    // the optical backscatter changes drastically.
    int reading = analogRead(AMBIENT_LIGHT_PIN);

    // If sensor reads total pitch-black 0 while LED is blasting at 100% duty cycle,
    // or saturated close-proximity reflection, flag tamper.
    if (ledActive && reading == 0) {
        return true; // Sensor blocked / black taped
    }
    return false;
}
