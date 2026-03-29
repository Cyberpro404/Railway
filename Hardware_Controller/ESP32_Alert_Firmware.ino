/*
 * ESP32 Alert System with Blynk Cloud Notification
 * Receives serial commands from backend and triggers Blynk events on state transitions
 */

#define BLYNK_TEMPLATE_ID "YOUR_TEMPLATE_ID"
#define BLYNK_TEMPLATE_NAME "Railway Monitor"
#define BLYNK_AUTH_TOKEN "YOUR_AUTH_TOKEN"

#include <WiFi.h>
#include <BlynkSimpleEsp32.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Hardware
const int LED_PIN = 2;  // Built-in LED on most ESP32 boards

// State tracking
char last_state = '0';  // Previous alert state ('0' or '1')
bool led_state = false;

void setup() {
  // Initialize serial at 115200 baud (matches Hardware_Controller)
  Serial.begin(115200);
  
  // Initialize LED pin
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  
  // Connect to Blynk
  Blynk.config(BLYNK_AUTH_TOKEN);
  Blynk.connect();
  
  last_state = '0';
}

void loop() {
  // Maintain Blynk connection (non-blocking)
  Blynk.run();
  
  // Check for incoming serial data
  if (Serial.available() > 0) {
    char incoming = Serial.read();
    
    // Only process '0' or '1' commands
    if (incoming == '0' || incoming == '1') {
      
      // Detect state transition: OFF -> ON
      if (last_state == '0' && incoming == '1') {
        // Alert condition triggered
        digitalWrite(LED_PIN, HIGH);
        led_state = true;
        
        // Send Blynk notification (only once on transition)
        Blynk.logEvent("alert", "Railway alert condition detected!");
      }
      // Detect state transition: ON -> OFF
      else if (last_state == '1' && incoming == '0') {
        // Alert condition cleared
        digitalWrite(LED_PIN, LOW);
        led_state = false;
      }
      // If incoming == last_state, do nothing (no transition)
      
      // Update state tracker
      last_state = incoming;
    }
  }
}
