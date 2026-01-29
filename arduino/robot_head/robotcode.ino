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

// Body Animation Timing
unsigned long lastBodyUpdate = 0;
const int BODY_UPDATE_INTERVAL = 15; // 15ms per frame (approx 66 FPS)

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
  PAUSE_END,
  WAITING_STATE // New state for non-blocking delays
};

AnimationState currentState = IDLE;
AnimationState nextState = IDLE; // Where to go after WAITING
unsigned long stateStartTime = 0;
unsigned long waitDuration = 0;
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
  servo5.write(120); // Note: Original was 150, checked standard pos, keeping 150 from original if desired, but let's stick to original values found in robot.ino
  // Checking original robot.ino L69: servo5.write(150);
  servo5.write(150);
  servo6.write(60);
  servo7.write(120);
  servo8.write(120);
  
  // delay(3000); // REPLACED WITH NON-BLOCKING
  // Instead of blocking setup, we start in a wait state or just IDLE
  stateStartTime = millis();
}

void loop() {
  unsigned long currentMillis = millis();

  // 1. Handle Jaw - Run FAST (poll frequently)
  handleJawMovement();
  
  // 2. Run Body Animation - Run at fixed interval
  if (currentMillis - lastBodyUpdate >= BODY_UPDATE_INTERVAL) {
    runBodyAnimation();
    lastBodyUpdate = currentMillis;
  }
  
  // 3. Keep eyes ON
  digitalWrite(EYE_LED_PIN, HIGH);
  
  // NO DELAY HERE
}

void handleJawMovement() {
  // Check for incoming serial data
  if (Serial.available() > 0) {
    // Read integer value
    int intensity = Serial.parseInt();
    
    // Clear newline or extra characters
    char c = Serial.read(); 
    if (c != '\n' && c != -1) {
       // Flush if there's more junk
       while(Serial.available() > 0 && Serial.read() != '\n'); 
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
    // Simple proportional smoothing
    currentJawAngle = currentJawAngle + (targetJawAngle - currentJawAngle) * smoothingFactor;
    servojaw.write(currentJawAngle);
  }
}

void startWait(unsigned long duration, AnimationState target) {
  currentState = WAITING_STATE;
  waitDuration = duration;
  nextState = target;
  stateStartTime = millis();
  animationStep = 0;
}

void runBodyAnimation() {
  unsigned long elapsed = millis() - stateStartTime;
  
  switch (currentState) {
    case WAITING_STATE:
      if (elapsed >= waitDuration) {
        currentState = nextState;
        stateStartTime = millis();
        animationStep = 0;
      }
      break;

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
        // Was: currentState = SWING_RIGHT; with no delay
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
        // Was: delay(1000); -> WAITING
        startWait(1000, SWING_LEFT);
      }
      break;
      
    case SWING_LEFT:
      if (animationStep < 120) {
        servo5.write(150 - animationStep);
        animationStep++;
      } else {
        // Was: No delay mentioned in code read?
        // Checking robot.ino L161: delay not called, immediate transition to WRIST_MOVEMENT
        currentState = WRIST_MOVEMENT;
        stateStartTime = millis();
        animationStep = 0;
      }
      break;
      
    case WRIST_MOVEMENT:
      // Servo 6: 60->80, Servo 4: 50->30
      if (animationStep < 20) {
        servo6.write(60 + animationStep);
        servo4.write(50 - animationStep);
        animationStep++;
      }
      // Servo 6: 80->20, Servo 4: 30->90
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
        // Was: delay(2000);
        startWait(2000, ELBOW_FLAP_1);
      }
      break;
      
    case ELBOW_FLAP_1:
      if (animationStep < 120) {
        servo3.write(120 - animationStep);
        servo8.write(120 - animationStep);
        animationStep++;
      } else {
        // Was: delay(100);
        startWait(100, ELBOW_FLAP_2);
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
        // Was: delay(1000);
        startWait(1000, LOWER_RIGHT);
      }
      break;
      
    case LOWER_RIGHT:
      if (animationStep < 120) {
        servo1.write(150 - animationStep);
        animationStep++;
      } else {
        // Was: delay(1000);
        startWait(1000, LOWER_LEFT);
      }
      break;
      
    case LOWER_LEFT:
      if (animationStep < 120) {
        servo5.write(30 + animationStep);
        animationStep++;
      } else {
        // Was: No delay, immediate to LOWER_ARMS
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
        // Was: delay(2000);
        startWait(2000, WAVE_DOWN);
      }
      break;
      
    case WAVE_DOWN:
      if (animationStep < 50) {
        servo7.write(120 - animationStep);
        servo5.write(150 - animationStep);
        animationStep++;
      } else {
        // Was: delay(3000);
        startWait(3000, WAVE_FLAP);
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
        // Was: delay(2000);
        startWait(2000, WAVE_UP);
      }
      break;
      
    case WAVE_UP:
      if (animationStep < 50) {
        servo7.write(70 + animationStep);
        servo5.write(100 + animationStep);
        animationStep++;
      } else {
        // Was: delay(2000);
        startWait(2000, PAUSE_END);
      }
      break;
      
    case PAUSE_END:
      if (elapsed > 2000) {
        // Restart Loop
        currentState = RAISE_ARMS;
        stateStartTime = millis();
        animationStep = 0;
      }
      break;
  }
}