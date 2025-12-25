#include <Servo.h>

// Servo Objects
Servo servo1, servo2, servo3, servo4;
Servo servo5, servo6, servo7, servo8;
Servo servojaw;

// Pin Definitions
const int EYE_LED_PIN = A1;

// Jaw Configuration
const int JAW_CLOSED_ANGLE = 50;
const int JAW_OPEN_ANGLE = 110;
int currentJawAngle = JAW_CLOSED_ANGLE;
int targetJawAngle = JAW_CLOSED_ANGLE;
float smoothingFactor = 0.3;

// Safety Timeout
unsigned long lastCommandTime = 0;
const unsigned long TIMEOUT_MS = 500;

// Animation State Machine
enum AnimationState {
  IDLE,
  RAISE_ARMS,
  SWING_RIGHT,
  SWING_LEFT,
  WRIST_MOVEMENT,
  ELBOW_FLAP_1,
  ELBOW_FLAP_2,
  LOWER_RIGHT,
  LOWER_LEFT,
  LOWER_ARMS,
  WAVE_DOWN,
  WAVE_FLAP,
  WAVE_UP,
  PAUSE_END
};

AnimationState currentState = IDLE;
unsigned long stateStartTime = 0;
int animationStep = 0;

void setup() {
  // Initialize Serial
  Serial.begin(115200);
  
  // Attach Servos
  servojaw.attach(7);
  servo1.attach(9);
  servo2.attach(10);
  servo3.attach(6);
  servo4.attach(5);
  servo5.attach(11);
  servo6.attach(12);
  servo7.attach(8);
  servo8.attach(4);
  
  // Initialize Eyes
  pinMode(EYE_LED_PIN, OUTPUT);
  digitalWrite(EYE_LED_PIN, HIGH);
  
  // Set normal positions
  servojaw.write(JAW_CLOSED_ANGLE);
  servo1.write(30);
  servo2.write(120);
  servo4.write(60);
  servo3.write(120);
  servo5.write(150);
  servo6.write(60);
  servo7.write(120);
  servo8.write(120);
  
  delay(3000);
  stateStartTime = millis();
}

void loop() {
  // Handle Jaw Movement via Serial
  handleJawMovement();
  
  // Run Body Animation State Machine
  runBodyAnimation();
  
  // Keep eyes ON
  digitalWrite(EYE_LED_PIN, HIGH);
  
  delay(15);
}

void handleJawMovement() {
  // Check for incoming serial data
  if (Serial.available() > 0) {
    int intensity = Serial.parseInt();
    
    // Clear buffer
    while (Serial.available() > 0) {
      Serial.read();
    }
    
    lastCommandTime = millis();
    targetJawAngle = map(intensity, 0, 100, JAW_CLOSED_ANGLE, JAW_OPEN_ANGLE);
    targetJawAngle = constrain(targetJawAngle, JAW_CLOSED_ANGLE, JAW_OPEN_ANGLE);
  }
  
  // Safety Timeout
  if (millis() - lastCommandTime > TIMEOUT_MS) {
    targetJawAngle = JAW_CLOSED_ANGLE;
  }
  
  // Smooth jaw movement
  if (abs(currentJawAngle - targetJawAngle) > 0) {
    currentJawAngle = currentJawAngle + (targetJawAngle - currentJawAngle) * smoothingFactor;
    servojaw.write(currentJawAngle);
  }
}

void runBodyAnimation() {
  unsigned long elapsed = millis() - stateStartTime;
  
  switch (currentState) {
    case IDLE:
      if (elapsed > 100) {
        currentState = RAISE_ARMS;
        stateStartTime = millis();
        animationStep = 0;
      }
      break;
      
    case RAISE_ARMS:
      if (animationStep < 60) {
        servo2.write(120 - animationStep);
        servo7.write(120 - animationStep);
        animationStep++;
      } else {
        currentState = SWING_RIGHT;
        stateStartTime = millis();
        animationStep = 0;
      }
      break;
      
    case SWING_RIGHT:
      if (animationStep < 120) {
        servo1.write(30 + animationStep);
        animationStep++;
      } else {
        currentState = SWING_LEFT;
        stateStartTime = millis();
        animationStep = 0;
        delay(1000);
      }
      break;
      
    case SWING_LEFT:
      if (animationStep < 120) {
        servo5.write(150 - animationStep);
        animationStep++;
      } else {
        currentState = WRIST_MOVEMENT;
        stateStartTime = millis();
        animationStep = 0;
      }
      break;
      
    case WRIST_MOVEMENT:
      // Servo 6: 60→80, Servo 4: 50→30
      if (animationStep < 20) {
        servo6.write(60 + animationStep);
        servo4.write(50 - animationStep);
        animationStep++;
      }
      // Servo 6: 80→20, Servo 4: 30→90
      else if (animationStep < 80) {
        int step = animationStep - 20;
        servo6.write(80 - step);
        servo4.write(30 + step);
        animationStep++;
      }
      // Return to normal
      else if (animationStep < 120) {
        int step = animationStep - 80;
        servo6.write(20 + step);
        servo4.write(90 - step);
        animationStep++;
      } else {
        currentState = ELBOW_FLAP_1;
        stateStartTime = millis();
        animationStep = 0;
        delay(2000);
      }
      break;
      
    case ELBOW_FLAP_1:
      if (animationStep < 120) {
        servo3.write(120 - animationStep);
        servo8.write(120 - animationStep);
        animationStep++;
      } else {
        currentState = ELBOW_FLAP_2;
        stateStartTime = millis();
        animationStep = 0;
        delay(100);
      }
      break;
      
    case ELBOW_FLAP_2:
      if (animationStep < 120) {
        servo3.write(animationStep);
        servo8.write(animationStep);
        animationStep++;
      } else if (animationStep < 240) {
        servo3.write(240 - animationStep);
        servo8.write(240 - animationStep);
        animationStep++;
      } else if (animationStep < 360) {
        servo3.write(animationStep - 240);
        servo8.write(animationStep - 240);
        animationStep++;
      } else {
        currentState = LOWER_RIGHT;
        stateStartTime = millis();
        animationStep = 0;
        delay(1000);
      }
      break;
      
    case LOWER_RIGHT:
      if (animationStep < 120) {
        servo1.write(150 - animationStep);
        animationStep++;
      } else {
        currentState = LOWER_LEFT;
        stateStartTime = millis();
        animationStep = 0;
        delay(1000);
      }
      break;
      
    case LOWER_LEFT:
      if (animationStep < 120) {
        servo5.write(30 + animationStep);
        animationStep++;
      } else {
        currentState = LOWER_ARMS;
        stateStartTime = millis();
        animationStep = 0;
      }
      break;
      
    case LOWER_ARMS:
      if (animationStep < 60) {
        servo2.write(60 + animationStep);
        servo7.write(60 + animationStep);
        animationStep++;
      } else {
        currentState = WAVE_DOWN;
        stateStartTime = millis();
        animationStep = 0;
        delay(2000);
      }
      break;
      
    case WAVE_DOWN:
      if (animationStep < 50) {
        servo7.write(120 - animationStep);
        servo5.write(150 - animationStep);
        animationStep++;
      } else {
        currentState = WAVE_FLAP;
        stateStartTime = millis();
        animationStep = 0;
        delay(3000);
      }
      break;
      
    case WAVE_FLAP:
      if (animationStep < 60) {
        servo3.write(animationStep * 2);
        servo8.write(animationStep * 2);
        animationStep++;
      } else if (animationStep < 120) {
        servo3.write(240 - animationStep * 2);
        servo8.write(240 - animationStep * 2);
        animationStep++;
      } else {
        currentState = WAVE_UP;
        stateStartTime = millis();
        animationStep = 0;
        delay(2000);
      }
      break;
      
    case WAVE_UP:
      if (animationStep < 50) {
        servo7.write(70 + animationStep);
        servo5.write(100 + animationStep);
        animationStep++;
      } else {
        currentState = PAUSE_END;
        stateStartTime = millis();
        animationStep = 0;
        delay(2000);
      }
      break;
      
    case PAUSE_END:
      if (elapsed > 2000) {
        // Reset to start of animation sequence - CONTINUOUS LOOP
        currentState = RAISE_ARMS;
        stateStartTime = millis();
        animationStep = 0;
      }
      break;
  }
}