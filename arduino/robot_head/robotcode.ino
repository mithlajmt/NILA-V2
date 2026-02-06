#include <Servo.h>

// Jaw Servo
Servo servojaw;

// Jaw Configuration
const int JAW_CLOSED_ANGLE = 50;   // Fully closed position
const int JAW_OPEN_ANGLE = 110;    // Fully open position
int currentJawAngle = JAW_CLOSED_ANGLE;
int targetJawAngle = JAW_CLOSED_ANGLE;

// Smoothing factor (0.0 - 1.0)
// Lower = smoother but slower response
// Higher = faster but more jerky
float smoothingFactor = 0.3;

// Safety Timeout - Close jaw if no data received
unsigned long lastCommandTime = 0;
const unsigned long TIMEOUT_MS = 500;  // 500ms timeout

void setup() {
  // Initialize Serial Communication
  Serial.begin(115200);
  
  // Attach Jaw Servo to Pin 7
  servojaw.attach(7);
  
  // Set jaw to closed position
  servojaw.write(JAW_CLOSED_ANGLE);
  
  Serial.println("Jaw Controller Ready");
  Serial.println("Waiting for intensity values (0-100)...");
}

void loop() {
  // Check for incoming serial data
  if (Serial.available() > 0) {
    // Read intensity value (0-100)
    int intensity = Serial.parseInt();
    
    // Clear any remaining characters in buffer
    while(Serial.available() > 0) {
      Serial.read();
    }
    
    // Update last command time
    lastCommandTime = millis();
    
    // Map intensity (0-100) to jaw angle (CLOSED-OPEN)
    targetJawAngle = map(intensity, 0, 100, JAW_CLOSED_ANGLE, JAW_OPEN_ANGLE);
    
    // Constrain to valid range
    targetJawAngle = constrain(targetJawAngle, JAW_CLOSED_ANGLE, JAW_OPEN_ANGLE);
  }
  
  // Safety Timeout - Close jaw if no data received for TIMEOUT_MS
  if (millis() - lastCommandTime > TIMEOUT_MS) {
    targetJawAngle = JAW_CLOSED_ANGLE;
  }
  
  // Smooth jaw movement using exponential smoothing
  // This creates natural, fluid motion instead of jerky movements
  if (abs(currentJawAngle - targetJawAngle) > 0.5) {
    currentJawAngle = currentJawAngle + (targetJawAngle - currentJawAngle) * smoothingFactor;
    servojaw.write(currentJawAngle);
  }
  
  // Small delay to prevent overwhelming the servo
  delay(10);
}