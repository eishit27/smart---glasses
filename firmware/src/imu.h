#ifndef IMU_H
#define IMU_H

#include <Arduino.h>
#include <Wire.h>

struct IMUData {
  float ax, ay, az; // Accelerometer in g
  float gx, gy, gz; // Gyroscope in degrees/sec
  float pitch;      // Estimated pitch in degrees
  float roll;       // Estimated roll in degrees
};

class IMUDriver {
public:
  IMUDriver(uint8_t sda_pin = 4, uint8_t scl_pin = 5);
  bool begin();
  bool readSensor(IMUData &out);

private:
  uint8_t _sda;
  uint8_t _scl;
  static const uint8_t MPU6050_ADDR = 0x68;
};

#endif // IMU_H
