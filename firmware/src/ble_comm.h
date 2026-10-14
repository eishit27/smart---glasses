#ifndef BLE_COMM_H
#define BLE_COMM_H

#include <stdint.h>
#include <stddef.h>

class BLEComm {
public:
    static void init();
    static void process();
    
    // Send full JPEG frame chunked over BLE (only if authenticated)
    static void sendFrame(const uint8_t* data, size_t len);
    
    // Send simple control command/status
    static void sendCommand(uint8_t cmd);
    
    // Check connection and security status
    static bool isConnected();
    static bool isAuthenticated();
    
    // Force disconnect (e.g. on auth failure or tamper alert)
    static void disconnect();
};

#endif // BLE_COMM_H
