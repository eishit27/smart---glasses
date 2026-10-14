#ifndef CAMERA_H
#define CAMERA_H

#include <esp_camera.h>

class Camera {
public:
    // Initialize OV2640 with configured pins
    static bool init();
    
    // Capture a frame, returns pointer to frame buffer
    static camera_fb_t* capture();
    
    // Release the frame buffer after use
    static void release(camera_fb_t* fb);
    
    // Power management for camera sensor
    static void setPower(bool enable);
};

#endif // CAMERA_H
