#ifndef PRIVACY_H
#define PRIVACY_H

class Privacy {
public:
    static void init();
    
    // Turn the privacy LED on or off (must be ON before camera operates)
    static void setLed(bool enable);
    static bool isLedActive();
    
    // Check if the ambient light sensor detects tampering/covering
    static bool isCovered();
};

#endif // PRIVACY_H
