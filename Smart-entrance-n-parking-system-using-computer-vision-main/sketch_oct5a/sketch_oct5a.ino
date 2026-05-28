#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "SHWqawqe";
const char* password = "234567";

// Server URL (replace with your server IP)
const char* serverURL = "http://192.168.43.40:8000";


// Pin definitions
#define PIR_ENTRY_PIN 13        // PIR sensor at entry gate
#define PIR_EXIT_PIN 14         // PIR sensor at exit gate
#define SERVO_PIN 15            // Servo motor for entry gate
#define LED_GREEN 2             // Green LED - authorized
#define LED_RED 4               // Red LED - not authorized

// Camera pins (ESP32-CAM specific - if using ESP32-CAM)
// If using external WiFi cam, these aren't needed
#define CAMERA_ENABLED false    // Set to true if using ESP32-CAM

Servo gateServo;

// State variables
bool entryDetected = false;
bool exitDetected = false;
unsigned long lastEntryTime = 0;
unsigned long lastExitTime = 0;
const unsigned long DEBOUNCE_DELAY = 3000; // 3 seconds debounce

// Current parking info
String currentPlate = "";
String currentSlot = "";

void setup() {
  Serial.begin(115200);
  
  // Initialize pins
  pinMode(PIR_ENTRY_PIN, INPUT);
  pinMode(PIR_EXIT_PIN, INPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  
  // Initialize servo
  gateServo.attach(SERVO_PIN);
  gateServo.write(0); // Gate closed position
  
  // Turn off LEDs initially
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_RED, LOW);
  
  // Connect to WiFi
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  
  Serial.println("ESP32 Parking System Ready!");
}

void loop() {
  // Check entry gate PIR sensor
  if (digitalRead(PIR_ENTRY_PIN) == HIGH && 
      (millis() - lastEntryTime > DEBOUNCE_DELAY)) {
    lastEntryTime = millis();
    Serial.println("\n[ENTRY] Vehicle detected at entry gate!");
    handleEntryGate();
  }
  
  // Check exit gate PIR sensor
  if (digitalRead(PIR_EXIT_PIN) == HIGH && 
      (millis() - lastExitTime > DEBOUNCE_DELAY)) {
    lastExitTime = millis();
    Serial.println("\n[EXIT] Vehicle detected at exit gate!");
    handleExitGate();
  }
  
  delay(100);
}

void handleEntryGate() {
  // Blink red LED to show processing
  digitalWrite(LED_RED, HIGH);
  delay(200);
  digitalWrite(LED_RED, LOW);
  
  Serial.println("Capturing image and checking authorization...");
  
  // Make API call to server
  HTTPClient http;
  String endpoint = String(serverURL) + "/api/entry_request";
  http.begin(endpoint);
  http.addHeader("Content-Type", "application/json");
  
  // Prepare JSON payload
  StaticJsonDocument<256> doc;
  
  // OPTION 1: Use preloaded image (for testing)
  doc["capture_mode"] = "preloaded";
  doc["image_name"] = "num.jpg";  // Change this to your test image
  
  // OPTION 2: Use webcam (comment out option 1, uncomment this)
  // doc["capture_mode"] = "webcam";
  // doc["camera_index"] = 0;
  
  // OPTION 3: Use WiFi camera (comment out option 1, uncomment this)
  // doc["capture_mode"] = "wificam";
  // doc["cam_url"] = "http://192.168.1.50:8080/video";  // Your WiFi cam URL
  
  String jsonPayload;
  serializeJson(doc, jsonPayload);
  
  Serial.println("Sending request: " + jsonPayload);
  
  int httpCode = http.POST(jsonPayload);
  
  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("Response: " + response);
    
    // Parse response
    StaticJsonDocument<512> responseDoc;
    DeserializationError error = deserializeJson(responseDoc, response);
    
    if (!error) {
      bool authorized = responseDoc["authorized"];
      
      if (authorized) {
        // Vehicle is authorized
        String plate = responseDoc["plate"].as<String>();
        String slot = responseDoc["slot"].as<String>();
        
        currentPlate = plate;
        currentSlot = slot;
        
        Serial.println("✓ AUTHORIZED - Plate: " + plate + ", Slot: " + slot);
        
        // Green LED on
        digitalWrite(LED_GREEN, HIGH);
        
        // Open gate
        openGate();
        
        // Wait for vehicle to pass
        delay(5000);
        
        // Close gate
        closeGate();
        
        // Turn off green LED
        digitalWrite(LED_GREEN, LOW);
        
      } else {
        // Vehicle not authorized
        String reason = responseDoc["reason"].as<String>();
        String plate = responseDoc["plate"].as<String>();
        
        Serial.println("✗ NOT AUTHORIZED - Reason: " + reason);
        if (plate != "null" && plate.length() > 0) {
          Serial.println("  Detected plate: " + plate);
        }
        
        // Red LED blink pattern (3 times)
        for (int i = 0; i < 3; i++) {
          digitalWrite(LED_RED, HIGH);
          delay(300);
          digitalWrite(LED_RED, LOW);
          delay(300);
        }
      }
    } else {
      Serial.println("Failed to parse JSON response");
      blinkError();
    }
  } else {
    Serial.print("HTTP Request failed, error: ");
    Serial.println(http.errorToString(httpCode));
    blinkError();
  }
  
  http.end();
}

void handleExitGate() {
  Serial.println("Vehicle exiting...");
  
  // Make exit request to server
  HTTPClient http;
  String endpoint = String(serverURL) + "/api/exit_request";
  http.begin(endpoint);
  http.addHeader("Content-Type", "application/json");
  
  StaticJsonDocument<256> doc;
  
  // OPTION 1: Use preloaded image (for testing)
  doc["capture_mode"] = "preloaded";
  doc["image_name"] = "num.jpg";  // Change this to your test image
  
  // OPTION 2: Use webcam (comment out option 1, uncomment this)
  // doc["capture_mode"] = "webcam";
  // doc["camera_index"] = 0;
  
  // OPTION 3: Use WiFi camera (comment out option 1, uncomment this)
  // doc["capture_mode"] = "wificam";
  // doc["cam_url"] = "http://192.168.1.50:8080/video";
  
  String jsonPayload;
  serializeJson(doc, jsonPayload);
  
  Serial.println("Sending exit request: " + jsonPayload);
  
  int httpCode = http.POST(jsonPayload);
  
  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("Exit response: " + response);
    
    // Parse response
    StaticJsonDocument<512> responseDoc;
    DeserializationError error = deserializeJson(responseDoc, response);
    
    if (!error) {
      bool success = responseDoc["success"];
      
      if (success) {
        String plate = responseDoc["plate"].as<String>();
        String slot = responseDoc["slot"].as<String>();
        
        Serial.println("✓ EXIT SUCCESSFUL - Plate: " + plate + ", Freed Slot: " + slot);
        
        // Blink green LED twice to confirm exit
        for (int i = 0; i < 2; i++) {
          digitalWrite(LED_GREEN, HIGH);
          delay(200);
          digitalWrite(LED_GREEN, LOW);
          delay(200);
        }
        
        // Clear current parking info if it matches
        if (currentSlot == slot) {
          currentPlate = "";
          currentSlot = "";
        }
      } else {
        String reason = responseDoc["reason"].as<String>();
        Serial.println("✗ EXIT ISSUE - Reason: " + reason);
        
        // Single red blink
        digitalWrite(LED_RED, HIGH);
        delay(500);
        digitalWrite(LED_RED, LOW);
      }
    } else {
      Serial.println("Failed to parse exit response");
      blinkError();
    }
  } else {
    Serial.print("Exit request failed, error: ");
    Serial.println(http.errorToString(httpCode));
    blinkError();
  }
  
  http.end();
}

void openGate() {
  Serial.println("Opening gate...");
  gateServo.write(90);  // Open position (adjust angle as needed)
}

void closeGate() {
  Serial.println("Closing gate...");
  gateServo.write(0);   // Closed position
}

void blinkError() {
  // Rapid blink both LEDs to indicate error
  for (int i = 0; i < 5; i++) {
    digitalWrite(LED_RED, HIGH);
    digitalWrite(LED_GREEN, HIGH);
    delay(100);
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_GREEN, LOW);
    delay(100);
  }
}
