#ifndef HAPTIC_H
#define HAPTIC_H

enum HapticPattern {
    HAPTIC_PATTERN_PULSE,
    HAPTIC_PATTERN_CONTINUOUS,
    HAPTIC_PATTERN_SOS,
    HAPTIC_PATTERN_WARNING
};

class Haptic {
public:
    static void init();
    static void update(); // Call in loop for non-blocking haptic
    
    // Play pattern, optionally limit duration (0 = full pattern)
    static void playPattern(HapticPattern pattern, unsigned long durationMs = 0);
    static void stop();
};

#endif // HAPTIC_H
