#include <Arduino_Modulino.h>
#include "Arduino_RouterBridge.h"

// =====================================================
// Modulino sensors
// =====================================================
ModulinoDistance distanceSensor;
ModulinoMovement movementSensor;
ModulinoLight lightSensor;

// Sensor initialization status
bool distanceOK = false;
bool movementOK = false;
bool lightOK = false;

float current_distance_mm = -1;
unsigned long lastDistanceUpdate = 0;
float current_accelX = 0, current_accelY = 0, current_accelZ = 0;
float current_gyroX = 0, current_gyroY = 0, current_gyroZ = 0;
int current_lightLux = -1, current_lightRaw = -1, current_lightIR = -1;

// =====================================================
// Function called from Python through Bridge
// =====================================================
String readSensors() {

  String data = "{";
  data += "\"distance_mm\":" + String(current_distance_mm, 1) + ",";
  data += "\"accel_x\":" + String(current_accelX, 3) + ",";
  data += "\"accel_y\":" + String(current_accelY, 3) + ",";
  data += "\"accel_z\":" + String(current_accelZ, 3) + ",";
  data += "\"gyro_x\":" + String(current_gyroX, 3) + ",";
  data += "\"gyro_y\":" + String(current_gyroY, 3) + ",";
  data += "\"gyro_z\":" + String(current_gyroZ, 3) + ",";
  data += "\"light_lux\":" + String(current_lightLux) + ",";
  data += "\"light_raw\":" + String(current_lightRaw) + ",";
  data += "\"light_ir\":" + String(current_lightIR) + ",";
  data += "\"distance_ok\":" + String(distanceOK ? "true" : "false") + ",";
  data += "\"movement_ok\":" + String(movementOK ? "true" : "false") + ",";
  data += "\"light_ok\":" + String(lightOK ? "true" : "false");
  data += "}";

  return data;
}

// =====================================================
// Arduino setup
// =====================================================
void setup() {
  Serial.begin(115200);
  Modulino.begin();
  delay(500);

  distanceOK = distanceSensor.begin();
  movementOK = movementSensor.begin();
  lightOK = lightSensor.begin();

  Bridge.begin();
  Bridge.provide("read_sensors", readSensors);
}

// =====================================================
// Arduino loop
// =====================================================
void loop() {
  Bridge.update();

    if (distanceSensor.available()) {
    float newDistance = distanceSensor.get();
    
    current_distance_mm = newDistance;
    lastDistanceUpdate = millis(); 

    Serial.print("NEW DISTANCE: ");
    Serial.println(newDistance);
  } else if (millis() - lastDistanceUpdate > 250) {
    current_distance_mm = -1.0; 
  }

  if (movementSensor.available()) {
    movementSensor.update();
    current_accelX = movementSensor.getX();
    current_accelY = movementSensor.getY();
    current_accelZ = movementSensor.getZ();
    current_gyroX = movementSensor.getRoll();
    current_gyroY = movementSensor.getPitch();
    current_gyroZ = movementSensor.getYaw();
  }

    lightSensor.update();
    current_lightLux = lightSensor.getLux();
    current_lightRaw = lightSensor.getAL();
    current_lightIR = lightSensor.getIR();


  delay(100);
}