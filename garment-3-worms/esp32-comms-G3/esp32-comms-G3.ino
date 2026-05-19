// Garment 3 (Worm) ESP32  
// Listens exclusively for background trigger signals from the Eye Pi ("PEEPING TOM")
// Communicates via hardware Serial to Arduino Mega at 9600 baud 

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h> 

// Network Settings 
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

// Static IP Configurations 
// This 200 corresponds to the Y placeholder in your Eye Pi Python script
IPAddress local_IP(192, 168, 1, 200); 
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

// IFTTT System Settings
const char* ifttt_key = "YOUR_IFTTT_KEY_HERE"; 
const char* event_name = "esp_ip_report";

WebServer server(80);

// Transmission token bound to the Arduino Mega sequence loop
const char TRIGGER_CHAR = 'T'; // Starts the cycle

// Background IP Reporting Function
void sendIPEmail(String ipAddress) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = "http://maker.ifttt.com/trigger/" + String(event_name) + "/with/key/" + String(ifttt_key);
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    String httpRequestData = "{\"value1\":\"worm_garment_" + ipAddress + "\"}";
    int httpResponseCode = http.POST(httpRequestData);
    http.end();
  }
}

// Background Route Trigger Handler
void handleTrigger() {
  // Transmits character token 'T' to the Arduino Mega
  Serial.write(TRIGGER_CHAR); 
  Serial.println("\nTrigger token dispatched to Mega: 'T'");
  server.send(200, "text/plain", "Trigger command sent to Arduino.");
}

void setup() {
  // Configured to 9600 to map directly to Arduino Mega Serial1 speed
  Serial.begin(9600); 
  delay(10);
  
  // Set Hostname for local identity verification
  WiFi.setHostname("worm-garment-esp32"); 

  // Mount networking parameters
  if (!WiFi.config(local_IP, gateway, subnet)) {
    Serial.println("STA Static IP Mask Configuration Error.");
  }

  Serial.print("Connecting to network: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n--- CONNECTED TO PRODUCTION INFRASTRUCTURE ---");
  Serial.print("Assigned IP Address: ");
  Serial.println(WiFi.localIP()); 
  Serial.println("----------------------------------------------");
  
  // Send network tracking confirmation via email
  sendIPEmail(WiFi.localIP().toString());

  // Web routes mappings (Only listening for the background trigger endpoint now)
  server.on("/trigger", handleTrigger);
  server.begin();
  
  Serial.println("HTTP background server active. System Ready.");
}

void loop() {
  // Non-blocking Auto-Reconnect Engine
  if (WiFi.status() != WL_CONNECTED) {
    static unsigned long lastAttempt = 0;
    if (millis() - lastAttempt > 5000) {
      WiFi.begin(ssid, password);
      lastAttempt = millis();
    }
  }
  
  server.handleClient();
}