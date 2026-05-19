// Mega Serial Communication Setup:
// ESP32 TX connects to Arduino Mega RX1 (Digital Pin 19)
// Both boards MUST share a common ground (GND)

// --- Pump and Valve Pin Definitions ---
// Pumps (PWM pins)
const int PUMP3 = 9;
const int PUMP2 = 8; 
const int PUMP1 = 7; 
const int PUMP8 = 4; 
const int PUMP10 = 6;
const int PUMP9 = 5; 

// Valves (Digital pins)
const int VALVE12 = 41; // 3
const int VALVE13 = 42; 
const int VALVE3 = 35; // 2
const int VALVE11 = 40; 
const int VALVE1 = 31;  // 1
const int VALVE2 = 33;  
const int VALVE14 = 43;  // 8
const int VALVE15 = 47;
const int VALVE6 = 30;  //10
const int VALVE7 = 32;
const int VALVE9 = 36;  //9 
const int VALVE10 = 38;

// --- System Constants ---
const int POWER = 240; // PWM value for running pumps (255 is 100%)
const int STOP = 0;    // PWM value for stopping pumps

const char TRIGGER_CHAR = 'T'; // Starts the cycle
const char STOP_CHAR = 'S';    // Stops the cycle immediately

// --- State Machine Variables ---
enum CycleState { STATE_STOPPED, STATE_RUNNING, STATE_FINISHED };
CycleState currentState = STATE_STOPPED;
int currentStep = 0; // Tracks the current stage in the cycle (1, 2, 3...)
unsigned long previousMillis = 0; // Stores the last time an action was taken
unsigned long interval = 0;     // Duration for the current step

// --- FUNCTION PROTOTYPES ---
void resetPins();
void stopAllActivity();
void runPumpValveCycleNonBlocking();

// Function to turn off all pumps and close all valves (used for internal pauses/deflation)
void resetPins() {
  // Stop all pumps
  analogWrite(PUMP1, STOP);
  analogWrite(PUMP2, STOP);
  analogWrite(PUMP3, STOP);
  analogWrite(PUMP8, STOP);
  analogWrite(PUMP9, STOP);
  analogWrite(PUMP10, STOP);

  // Close all valves (set to LOW)
  digitalWrite(VALVE1, LOW);
  digitalWrite(VALVE2, LOW);
  digitalWrite(VALVE3, LOW);
  digitalWrite(VALVE6, LOW);
  digitalWrite(VALVE7, LOW);
  digitalWrite(VALVE9, LOW);
  digitalWrite(VALVE10, LOW);
  digitalWrite(VALVE11, LOW);
  digitalWrite(VALVE12, LOW);
  digitalWrite(VALVE13, LOW);
  digitalWrite(VALVE14, LOW);
  digitalWrite(VALVE15, LOW);
  Serial.println("All pins reset.");
}

// Function to immediately halt all activity (used for the STOP button)
void stopAllActivity() {
  resetPins();
  currentState = STATE_STOPPED; // Force the state to stopped
  currentStep = 0;              // Reset step counter
  Serial.println("!!! IMMEDIATE STOP COMMAND RECEIVED. ALL ACTIVITY HALTED. !!!");
}

// Function containing the entire pump/valve sequence using a non-blocking state machine
void runPumpValveCycleNonBlocking() {
  unsigned long currentMillis = millis();

  // If the system is stopped, do nothing here.
  if (currentState == STATE_STOPPED) {
    return;
  }
  
  // Check if it's time to transition to the next step
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis; // Restart the timer
    currentStep++;                  // Move to the next step

    Serial.print("Executing Step: ");
    Serial.println(currentStep);

    // --- State Machine based on original cycle logic ---
    switch (currentStep) {
      case 1: // Start Cycle 1 - 1000ms
        interval = 1000;
        digitalWrite(VALVE12, HIGH); digitalWrite(VALVE13, LOW); analogWrite(PUMP3, POWER);
        digitalWrite(VALVE11, LOW); digitalWrite(VALVE3, LOW); analogWrite(PUMP2, STOP);
        digitalWrite(VALVE1, HIGH);  digitalWrite(VALVE2, LOW); analogWrite(PUMP1, POWER);
        digitalWrite(VALVE14, LOW); digitalWrite(VALVE15, LOW); analogWrite(PUMP8, STOP);
        digitalWrite(VALVE6, HIGH);  digitalWrite(VALVE7, LOW); analogWrite(PUMP10, POWER);
        digitalWrite(VALVE9, HIGH);  digitalWrite(VALVE10, LOW); analogWrite(PUMP9, POWER);
        break;

      case 2: // Hold Cycle 1 - 1000ms
        interval = 1000;
        digitalWrite(VALVE12, HIGH); digitalWrite(VALVE13, HIGH); analogWrite(PUMP3, STOP);
        digitalWrite(VALVE11, HIGH); digitalWrite(VALVE3, HIGH); analogWrite(PUMP2, STOP);
        digitalWrite(VALVE1, HIGH);  digitalWrite(VALVE2, HIGH); analogWrite(PUMP1, STOP);
        digitalWrite(VALVE14, HIGH); digitalWrite(VALVE15, HIGH); analogWrite(PUMP8, STOP);
        digitalWrite(VALVE6, HIGH);  digitalWrite(VALVE7, HIGH); analogWrite(PUMP10, STOP);
        digitalWrite(VALVE9, HIGH);  digitalWrite(VALVE10, HIGH); analogWrite(PUMP9, STOP);
        break;

      case 3: // Reverse Cycle 1 - 1000ms
        interval = 1000;
        digitalWrite(VALVE12, LOW);  digitalWrite(VALVE13, HIGH); analogWrite(PUMP3, POWER);
        digitalWrite(VALVE11, LOW);  digitalWrite(VALVE3, HIGH); analogWrite(PUMP2, POWER);
        digitalWrite(VALVE1, LOW);   digitalWrite(VALVE2, HIGH); analogWrite(PUMP1, POWER);
        digitalWrite(VALVE14, LOW);  digitalWrite(VALVE15, LOW); analogWrite(PUMP8, STOP);
        digitalWrite(VALVE6, LOW);   digitalWrite(VALVE7, HIGH); analogWrite(PUMP10, POWER);
        digitalWrite(VALVE9, LOW);   digitalWrite(VALVE10, HIGH); analogWrite(PUMP9, POWER);
        break;

      case 4: // Deflate (Reset Pins) - 1000ms
        interval = 600;
        resetPins();
        break;
      
      case 5: // Start Cycle 2 - 900ms
        interval = 1000;
        digitalWrite(VALVE12, HIGH); digitalWrite(VALVE13, LOW); analogWrite(PUMP3, POWER);
        digitalWrite(VALVE11, LOW);  digitalWrite(VALVE3, LOW); analogWrite(PUMP2, STOP);
        digitalWrite(VALVE1, HIGH);  digitalWrite(VALVE2, LOW); analogWrite(PUMP1, POWER);
        digitalWrite(VALVE14, LOW);  digitalWrite(VALVE15, LOW); analogWrite(PUMP8, STOP);
        digitalWrite(VALVE6, HIGH);  digitalWrite(VALVE7, LOW); analogWrite(PUMP10, POWER);
        digitalWrite(VALVE9, HIGH);  digitalWrite(VALVE10, LOW); analogWrite(PUMP9, POWER);
        break;

      case 6: // Hold Cycle 2 - 500ms
        interval = 500;
        digitalWrite(VALVE12, HIGH); digitalWrite(VALVE13, HIGH); analogWrite(PUMP3, STOP);
        digitalWrite(VALVE11, HIGH); digitalWrite(VALVE3, HIGH); analogWrite(PUMP2, STOP);
        digitalWrite(VALVE1, HIGH);  digitalWrite(VALVE2, HIGH); analogWrite(PUMP1, STOP);
        digitalWrite(VALVE14, LOW); digitalWrite(VALVE15, LOW); analogWrite(PUMP8, STOP);
        digitalWrite(VALVE6, HIGH);  digitalWrite(VALVE7, HIGH); analogWrite(PUMP10, STOP);
        digitalWrite(VALVE9, HIGH);  digitalWrite(VALVE10, HIGH); analogWrite(PUMP9, STOP);
        break;

      case 7: // Deflate (Reset Pins) - 900ms
        interval = 600;
        resetPins();
        break;

      case 8: // Reverse Cycle 2 - 800ms
        interval = 1000;
        digitalWrite(VALVE12, LOW);  digitalWrite(VALVE13, HIGH); analogWrite(PUMP3, STOP);
        digitalWrite(VALVE11, LOW); digitalWrite(VALVE3, LOW); analogWrite(PUMP2, STOP);
        digitalWrite(VALVE1, LOW);   digitalWrite(VALVE2, HIGH); analogWrite(PUMP1, POWER);
        digitalWrite(VALVE14, LOW);  digitalWrite(VALVE15, LOW); analogWrite(PUMP8, STOP);
        digitalWrite(VALVE6, LOW);   digitalWrite(VALVE7, HIGH); analogWrite(PUMP10, POWER);
        digitalWrite(VALVE9, HIGH);  digitalWrite(VALVE10, LOW); analogWrite(PUMP9, POWER);
        break;

      case 9: // Deflate (Reset Pins) - 800ms
        interval = 600;
        resetPins();
        break;

      case 10: // Start Cycle 3 - 400ms
        interval = 1000;
        digitalWrite(VALVE12, HIGH); digitalWrite(VALVE13, LOW); analogWrite(PUMP3, POWER);
        digitalWrite(VALVE11, LOW);  digitalWrite(VALVE3, HIGH); analogWrite(PUMP2, POWER);
        digitalWrite(VALVE1, HIGH);  digitalWrite(VALVE2, LOW); analogWrite(PUMP1, POWER);
        digitalWrite(VALVE14, LOW); digitalWrite(VALVE15, LOW); analogWrite(PUMP8, LOW);
        digitalWrite(VALVE6, HIGH);  digitalWrite(VALVE7, LOW); analogWrite(PUMP10, POWER);
        digitalWrite(VALVE9, LOW);   digitalWrite(VALVE10, HIGH); analogWrite(PUMP9, POWER);
        break;

      case 11: // Deflate (Reset Pins) - 900ms
        interval = 600;
        resetPins();
        break;

      case 12: // Reverse Cycle 3 (Part 1) - 1000ms
        interval = 1000;
        digitalWrite(VALVE12, LOW);  digitalWrite(VALVE13, LOW); analogWrite(PUMP3, STOP);
        digitalWrite(VALVE11, LOW); digitalWrite(VALVE3, LOW); analogWrite(PUMP2, STOP);
        digitalWrite(VALVE1, LOW);   digitalWrite(VALVE2, HIGH); analogWrite(PUMP1, POWER);
        digitalWrite(VALVE14, LOW);  digitalWrite(VALVE15, LOW); analogWrite(PUMP8, STOP);
        digitalWrite(VALVE6, LOW);   digitalWrite(VALVE7, HIGH); analogWrite(PUMP10, POWER);
        digitalWrite(VALVE9, HIGH);  digitalWrite(VALVE10, LOW); analogWrite(PUMP9, POWER);
        break;

      case 13: // Deflate (Reset Pins) - 800ms
        interval = 600;
        resetPins();
        break;

      case 14: // Start Cycle 3 (Part 2) - 1000ms
        interval = 1000;
        digitalWrite(VALVE12, HIGH); digitalWrite(VALVE13, LOW); analogWrite(PUMP3, POWER);
        digitalWrite(VALVE11, LOW); digitalWrite(VALVE3, HIGH); analogWrite(PUMP2, POWER);
        digitalWrite(VALVE1, HIGH);  digitalWrite(VALVE2, LOW); analogWrite(PUMP1, POWER);
        digitalWrite(VALVE14, LOW); digitalWrite(VALVE15, LOW); analogWrite(PUMP8, STOP);
        digitalWrite(VALVE6, HIGH);  digitalWrite(VALVE7, LOW); analogWrite(PUMP10, POWER);
        digitalWrite(VALVE9, HIGH);  digitalWrite(VALVE10, LOW); analogWrite(PUMP9, POWER);
        break;

      case 15: // Hold Cycle 3 - 1000ms
        interval = 1000;
        digitalWrite(VALVE12, HIGH); digitalWrite(VALVE13, HIGH); analogWrite(PUMP3, STOP);
        digitalWrite(VALVE11, HIGH); digitalWrite(VALVE3, HIGH); analogWrite(PUMP2, STOP);
        digitalWrite(VALVE1, HIGH);  digitalWrite(VALVE2, HIGH); analogWrite(PUMP1, STOP);
        digitalWrite(VALVE14, LOW); digitalWrite(VALVE15, LOW); analogWrite(PUMP8, STOP);
        digitalWrite(VALVE6, HIGH);  digitalWrite(VALVE7, HIGH); analogWrite(PUMP10, STOP);
        digitalWrite(VALVE9, HIGH);  digitalWrite(VALVE10, HIGH); analogWrite(PUMP9, STOP);
        break;

      case 16: // Reverse Cycle 3 (Part 3) - 1000ms
        interval = 1000;
        digitalWrite(VALVE12, LOW);  digitalWrite(VALVE13, HIGH); analogWrite(PUMP3, POWER);
        digitalWrite(VALVE11, LOW);  digitalWrite(VALVE3, HIGH); analogWrite(PUMP2, POWER);
        digitalWrite(VALVE1, LOW);   digitalWrite(VALVE2, HIGH); analogWrite(PUMP1, POWER);
        digitalWrite(VALVE14, LOW);  digitalWrite(VALVE15, LOW); analogWrite(PUMP8, STOP);
        digitalWrite(VALVE6, LOW);   digitalWrite(VALVE7, HIGH); analogWrite(PUMP10, POWER);
        digitalWrite(VALVE9, LOW);   digitalWrite(VALVE10, HIGH); analogWrite(PUMP9, POWER);
        break;

      case 17: // Final Deflate (Reset Pins) - 2000ms
        interval = 1000;
        resetPins();
        break;
      
      case 18: // Final Delay (Reset Pins) - 2000ms
        interval = 1000;
        resetPins();
        break;

      default:
        // Cycle completed all 18 steps, reset the counter to loop back to Step 1
        currentStep = 0; // Next iteration will be 1
        Serial.println("Cycle finished. Looping back to Step 1.");
        break;
    }
  }
}

void setup() {
  // Use Serial for debugging/monitor and Serial1 for communication with ESP32
  Serial.begin(9600);
  Serial1.begin(9600); // Initialize Serial1 for ESP32 communication

  // Pin Initialization (omitted for brevity, as it's the same as previous versions)

  pinMode(PUMP1, OUTPUT); pinMode(PUMP2, OUTPUT); pinMode(PUMP3, OUTPUT);
  pinMode(PUMP8, OUTPUT); pinMode(PUMP9, OUTPUT); pinMode(PUMP10, OUTPUT);

  pinMode(VALVE1, OUTPUT); pinMode(VALVE2, OUTPUT); pinMode(VALVE3, OUTPUT);
  pinMode(VALVE6, OUTPUT); pinMode(VALVE7, OUTPUT); pinMode(VALVE9, OUTPUT);
  pinMode(VALVE10, OUTPUT); pinMode(VALVE11, OUTPUT); pinMode(VALVE12, OUTPUT);
  pinMode(VALVE13, OUTPUT); pinMode(VALVE14, OUTPUT); pinMode(VALVE15, OUTPUT);

  // Initial State (STOP pumps, LOW valves)
  stopAllActivity(); 

  delay(1000); 
  Serial.println("Arduino Ready. Waiting for ESP32 trigger on Serial1...");
}

void loop() {
  // 1. Check for incoming serial commands from ESP32 first (High Priority)
  if (Serial1.available()) {
    char data = Serial1.read();
    
    if (data == TRIGGER_CHAR && currentState != STATE_RUNNING) {
      Serial.println("Trigger received, starting cycle...");
      currentState = STATE_RUNNING;
      currentStep = 0; // Will become 1 immediately after the loop runs
      previousMillis = millis(); 
    } else if (data == STOP_CHAR) {
      // If STOP character is received, halt immediately and reset state variables
      stopAllActivity(); // This sets currentState = STATE_STOPPED
    }
  }
  
  // 2. Run the non-blocking cycle logic if we are in the RUNNING state
  if (currentState == STATE_RUNNING) {
    runPumpValveCycleNonBlocking();
  }
}