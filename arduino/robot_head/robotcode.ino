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
unsigned long lastHeartbeatTime = 0;
const unsigned long HEARTBEAT_MS = 2000; // heartbeat every 2s

void setup() {
  // Initialize Serial Communication
  Serial.begin(115200);
  
  // Attach Jaw Servo to Pin 7 (or PA3 on STM32)
#if defined(PA3)
  servojaw.attach(PA3);
#else
  servojaw.attach(7);
#endif
  
  // Set jaw to closed position
  servojaw.write(JAW_CLOSED_ANGLE);
  
  // Initialize timeout
  lastCommandTime = millis();
  
  Serial.println("Jaw Controller Ready");
  Serial.println("Waiting for intensity values (0-100)...");
}

void loop() {
  // Check for incoming serial data
  if (Serial.available() > 0) {
    // Read a line until newline (more reliable than parseInt)
    char buffer[10];
    int len = Serial.readBytesUntil('\n', buffer, sizeof(buffer) - 1);
    
    if (len > 0) {
      buffer[len] = '\0';  // Null-terminate
      int intensity = atoi(buffer);  // Convert string to int
      
      // Ensure in valid range
      intensity = constrain(intensity, 0, 100);
      
      // Update last command time
      lastCommandTime = millis();
      
      // Map intensity (0-100) to jaw angle (CLOSED-OPEN)
      targetJawAngle = map(intensity, 0, 100, JAW_CLOSED_ANGLE, JAW_OPEN_ANGLE);
      
      // Constrain to valid range
      targetJawAngle = constrain(targetJawAngle, JAW_CLOSED_ANGLE, JAW_OPEN_ANGLE);
      
      // Debug: echo received intensity
      Serial.print("INTENSITY RECEIVED: ");
      Serial.println(intensity);
    }
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

  // Heartbeat when idle (helps verify sketch is running)
  if (millis() - lastHeartbeatTime > HEARTBEAT_MS) {
    lastHeartbeatTime = millis();
    Serial.println("HEARTBEAT");
  }
}