#include "imu.h"
#include <math.h>

IMUDriver::IMUDriver(uint8_t sda_pin, uint8_t scl_pin)
  : _sda(sda_pin), _scl(scl_pin) {}

bool IMUDriver::begin() {
  Wire.begin(_sda, _scl);
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x6B); // Power Management 1 register
  Wire.write(0x00); // Wake up MPU6050 from sleep
  uint8_t error = Wire.endTransmission();
  return (error == 0);
}

bool IMUDriver::readSensor(IMUData &out) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x3B); // Starting register for Accelerometer & Gyro measurements
  if (Wire.endTransmission(false) != 0) return false;

  uint8_t bytesRead = Wire.requestFrom((uint16_t)MPU6050_ADDR, (uint8_t)14, (uint8_t)true);
  if (bytesRead < 14) return false;

  int16_t raw_ax = (Wire.read() << 8) | Wire.read();
  int16_t raw_ay = (Wire.read() << 8) | Wire.read();
  int16_t raw_az = (Wire.read() << 8) | Wire.read();
  int16_t raw_temp = (Wire.read() << 8) | Wire.read();
  int16_t raw_gx = (Wire.read() << 8) | Wire.read();
  int16_t raw_gy = (Wire.read() << 8) | Wire.read();
  int16_t raw_gz = (Wire.read() << 8) | Wire.read();

  // Scale factors: +/- 2g range = 16384 LSB/g, +/- 250 deg/s range = 131 LSB/(deg/s)
  out.ax = (float)raw_ax / 16384.0f;
  out.ay = (float)raw_ay / 16384.0f;
  out.az = (float)raw_az / 16384.0f;

  out.gx = (float)raw_gx / 131.0f;
  out.gy = (float)raw_gy / 131.0f;
  out.gz = (float)raw_gz / 131.0f;

  // Compute roll and pitch from gravity vector
  out.roll  = atan2(out.ay, out.az) * 180.0f / M_PI;
  out.pitch = atan2(-out.ax, sqrt(out.ay * out.ay + out.az * out.az)) * 180.0f / M_PI;

  return true;
}
