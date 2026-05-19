// combined gpt logic with original pump design  - shortened to 10secs

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// --- PIN DEFINITIONS ---
const int PUMPS[5] = {7, 8, 9, 6, 5};
const int VALVES[5] = {31, 33, 35, 38, 36};
const int POWER = 220;
const int STOP = 0;
const int CENTER_ANGLE = 90;

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();
#define SERVOMIN  150 
#define SERVOMAX  600 
uint8_t servoChannels[4] = {4, 5, 6, 7};

// --- System State ---
int currentStep = 0;                     
unsigned long previousMillis = 0;        
unsigned long interval = 0;              
bool isRunning = false; 

int angleToPulse(int angle) {
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

void setAllPumpsValves(int power, bool valveOpen) {
  int valveState = valveOpen ? HIGH : LOW;
  for (int i = 0; i < 5; i++) {
    digitalWrite(VALVES[i], valveState);
    analogWrite(PUMPS[i], power);
  }
}

// Moves servos in a smooth arc within a specific time window
void moveCenterTargetCenter(int targetAngle, unsigned long totalTime, int repeats) {
  unsigned long startTime = millis();
  while (millis() - startTime < totalTime) {
    unsigned long elapsed = millis() - startTime;
    unsigned long cycleDuration = totalTime / repeats;
    unsigned long timeInCycle = elapsed % cycleDuration;
    float progress;

    if (timeInCycle < cycleDuration / 2) {
      progress = (float)timeInCycle / (cycleDuration / 2.0);
    } else {
      progress = 1.0 - ((float)(timeInCycle - (cycleDuration / 2.0)) / (cycleDuration / 2.0));
    }

    int currentAngle = CENTER_ANGLE + (int)((targetAngle - CENTER_ANGLE) * progress);
    for (int i = 0; i < 4; i++) {
      pwm.setPWM(servoChannels[i], 0, angleToPulse(currentAngle));
    }
    delay(15); 
  }
}

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);

  for (int i = 0; i < 5; i++) {
    pinMode(PUMPS[i], OUTPUT);
    pinMode(VALVES[i], OUTPUT);
  }
  
  pwm.begin();
  pwm.setPWMFreq(50);

  for (int i = 0; i < 4; i++) {
    pwm.setPWM(servoChannels[i], 0, angleToPulse(CENTER_ANGLE));
  }

  setAllPumpsValves(STOP, LOW);
  Serial.println("Mega Ready. Waiting for ESP32 '1'...");
}

void loop() {

  if (Serial1.available() > 0) {
    char incoming = Serial1.read();
    if (incoming == '1' && !isRunning) {
      Serial.println("TRIGGER CONFIRMED: Starting Sequence...");
      isRunning = true;
      currentStep = 0;
      previousMillis = millis();
      interval = 0;
    }
  }

  if (isRunning) {
    unsigned long currentMillis = millis();
    if (currentMillis - previousMillis >= interval) {
      previousMillis = currentMillis;
      currentStep++;

      switch (currentStep) {

        case 1: // Cycle 1: wide
          setAllPumpsValves(POWER, HIGH);
          moveCenterTargetCenter(150, 5000, 2);
          interval = 100;
          break;

        case 2: // Pause
          setAllPumpsValves(STOP, HIGH);
          interval = 2000;
          break;

        case 3: // Cycle 2: deep
          setAllPumpsValves(POWER, HIGH);
          moveCenterTargetCenter(30, 5000, 2);
          interval = 100;
          break;

        case 4: // Pause
          setAllPumpsValves(STOP, HIGH);
          interval = 2000;
          break;

        case 5: // Cycle 3: medium
          setAllPumpsValves(POWER, HIGH);
          moveCenterTargetCenter(120, 5000, 2);
          interval = 100;
          break;

        case 6: // Release
          setAllPumpsValves(STOP, LOW);
          for (int i = 0; i < 4; i++) {
            pwm.setPWM(servoChannels[i], 0, angleToPulse(CENTER_ANGLE));
          }
          isRunning = false;
          Serial.println("Sequence complete. Waiting for next trigger.");
          interval = 10000;
          break;
      }
    }
  }
}
