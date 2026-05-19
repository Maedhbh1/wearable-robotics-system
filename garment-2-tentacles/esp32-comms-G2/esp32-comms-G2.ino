// Garment 2 (Tentacle) ESP32  
// Listens exclusively for background trigger signals from the Eye Pi ("CREEP")
// Communicates via hardware Serial to Arduino Mega at 9600 baud 

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h> 

// Network Settings 

const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

// Static IP Configurations 
// This 103 corresponds to the X placeholder in your Eye Pi Python script
IPAddress local_IP(192, 168, 1, 103); 
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

// IFTTT System Settings
const char* ifttt_key = "YOUR_IFTTT_KEY_HERE"; 
const char* event_name = "esp_ip_report";

WebServer server(80);

void sendIPEmail(String ipAddress) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = "http://maker.ifttt.com/trigger/" + String(event_name) + "/with/key/" + String(ifttt_key);
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    String httpRequestData = "{\"value1\":\"" + ipAddress + "\"}";
    int httpResponseCode = http.POST(httpRequestData);
    http.end();
  }
}

void handleTrigger() {
  Serial.println("Trigger Received! Sending '1' to Mega...");
  Serial2.write('1');
  Serial2.flush();
  server.send(200, "text/plain", "Triggered");
}

void setup() {
  Serial.begin(115200); 
  Serial2.begin(115200, SERIAL_8N1, 16, 17);

  // Set Hostname for the Network
  // This tells the router "My name is esp32-B78D54"
  WiFi.setHostname("esp32-B78D54"); 

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected!");
  Serial.print("Assigned IP: ");
  Serial.println(WiFi.localIP());

  // Send email so you know exactly what IP the static name points to
  sendIPEmail(WiFi.localIP().toString());

  server.on("/trigger", handleTrigger);
  server.begin();
}

void loop() {
  // Non-blocking Auto-Reconnect
  if (WiFi.status() != WL_CONNECTED) {
    static unsigned long lastAttempt = 0;
    if (millis() - lastAttempt > 5000) {
      WiFi.begin(ssid, password);
      lastAttempt = millis();
    }
  }
  server.handleClient();
}