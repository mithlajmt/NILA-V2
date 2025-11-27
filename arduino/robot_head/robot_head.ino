/*
 * NILA-V2 Robot Head Controller
 * -----------------------------
 * Controls a servo for jaw movement and an LED for eyes.
 * Receives commands via Serial (USB).
 * 
 * Hardware:
 * - Servo: Pin 9
 * - Eye LED: Pin A1
 * 
 * Serial Protocol:
 * - Send integer 0-100 followed by newline.
 * - 0 = Jaw Closed (90 degrees)
 * - 100 = Jaw Open (130 degrees)
 * - Values in between map linearly.
 */

#include <Servo.h>

// Pin Definitions
const int SERVO_PIN = 9;
const int EYE_LED_PIN = A1;

// Servo Configuration
Servo jawServo;
const int JAW_CLOSED_ANGLE = 90;
const int JAW_OPEN_ANGLE = 130;

// Safety Timeout
unsigned long lastCommandTime = 0;
const unsigned long TIMEOUT_MS = 500; // Close jaw if no data for 500ms

void setup() {
  // Initialize Serial
  Serial.begin(115200);
  
  // Initialize Servo
  jawServo.attach(SERVO_PIN);
  jawServo.write(JAW_CLOSED_ANGLE); // Start closed
  
  // Initialize Eyes
  pinMode(EYE_LED_PIN, OUTPUT);
  digitalWrite(EYE_LED_PIN, HIGH); // Turn eyes ON
}

void loop() {
  // Check for incoming serial data
  if (Serial.available() > 0) {
    // Read integer from serial
    int intensity = Serial.parseInt();
    
    // Clear buffer
    while (Serial.available() > 0) {
      Serial.read();
    }
    
    // Update last command time
    lastCommandTime = millis();
    
    // Map intensity (0-100) to angle (90-130)
    int angle = map(intensity, 0, 100, JAW_CLOSED_ANGLE, JAW_OPEN_ANGLE);
    
    // Constrain angle just in case
    angle = constrain(angle, JAW_CLOSED_ANGLE, JAW_OPEN_ANGLE);
    
    // Move servo
    jawServo.write(angle);
  }
  
  // Safety Timeout: Close jaw if silence
  if (millis() - lastCommandTime > TIMEOUT_MS) {
    jawServo.write(JAW_CLOSED_ANGLE);
  }
  
  // Keep eyes ON
  digitalWrite(EYE_LED_PIN, HIGH);
}
