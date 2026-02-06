#include <Servo.h>

Servo s;
#if defined(PA3)
const int PIN = PA3;
#else
const int PIN = 7;
#endif

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("TEST: MCU alive - Servo test starting");
  s.attach(PIN);
}

void loop() {
  s.write(50); // closed
  Serial.println("TEST: servo -> 50");
  delay(1000);
  s.write(110); // open
  Serial.println("TEST: servo -> 110");
  delay(1000);
}
