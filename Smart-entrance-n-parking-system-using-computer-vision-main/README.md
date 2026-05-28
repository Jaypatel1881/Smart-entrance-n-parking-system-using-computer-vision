# Smart-entrance-n-parking-system-using-computer-vision
🚗 ESP32 Smart Parking System An intelligent automated parking management system using ESP32, computer vision, and license plate recognition. The system automatically detects vehicles, reads license plates using AI/OCR, verifies registration, controls entry gates, and manages parking slot allocation.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![ESP32](https://img.shields.io/badge/ESP32-IoT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

## 📋 Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

### Core Functionality
- ✅ **Automated Vehicle Detection** - PIR sensors detect vehicles at entry/exit gates
- 🔍 **AI-Powered License Plate Recognition** - Custom CNN + EasyOCR for accurate plate reading
- 🔐 **Registration Verification** - Database-backed vehicle authorization
- 🚪 **Automatic Gate Control** - Servo motor opens gate for authorized vehicles
- 🅿️ **Smart Slot Allocation** - Intelligent parking space management
- 📊 **Real-time Monitoring** - RESTful API for system status and analytics
- 📝 **Event Logging** - Complete entry/exit history with timestamps
- 💡 **Visual Feedback** - LED indicators for authorization status

### Advanced Features
- 🎯 **Improved Plate Detection** - Filters false readings (car brands, extra text)
- 🧹 **Text Cleaning** - Regex-based validation for Indian license plate formats
- 📸 **Multiple Capture Modes** - Preloaded images, webcam, or WiFi camera support
- 🔄 **Automatic Exit Processing** - Plate recognition at exit to free parking slots
- 🌐 **Web API** - Easy integration with dashboards and mobile apps

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Cloud/Server                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Python FastAPI Server (Computer/Raspberry Pi)      │   │
│  │  - License Plate Detection (CNN + EasyOCR)          │   │
│  │  - Database Management (SQLite)                     │   │
│  │  - RESTful API Endpoints                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↕ WiFi/HTTP
┌─────────────────────────────────────────────────────────────┐
│                      Edge Device (ESP32)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐       │
│  │  Entry PIR  │  │  Exit PIR   │  │ Servo Gate   │       │
│  │  Sensor     │  │  Sensor     │  │ Control      │       │
│  └─────────────┘  └─────────────┘  └──────────────┘       │
│  ┌─────────────┐  ┌─────────────┐                         │
│  │  Green LED  │  │  Red LED    │  Status Indicators      │
│  └─────────────┘  └─────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Vehicle Approaches → PIR Detects → ESP32 Captures Image
                                         ↓
                                  Send to Server
                                         ↓
                    ┌────────────────────┴────────────────────┐
                    ↓                                         ↓
            Detect License Plate                    Check Registration DB
                    ↓                                         ↓
            Extract Text (OCR)                        Is Registered?
                    ↓                                         ↓
            Clean & Validate                          ┌──────┴──────┐
                    ↓                                 YES            NO
            Return to ESP32                            ↓              ↓
                    ↓                          Allocate Slot    Deny Access
                    ↓                          Open Gate        Red LED
            Process Response                   Green LED       Gate Closed
```

## 🛠️ Hardware Requirements

### Components List

| Component | Quantity | Specifications | Purpose |
|-----------|----------|----------------|---------|
| ESP32 Development Board | 1 | ESP32-WROOM-32 | Main controller |
| PIR Motion Sensor | 2 | HC-SR501 | Vehicle detection |
| Servo Motor | 1 | SG90/MG995 | Gate control |
| LED - Green | 1 | 5mm, 3V | Authorized indicator |
| LED - Red | 1 | 5mm, 3V | Unauthorized indicator |
| Resistor 220Ω | 2 | 1/4W | LED current limiting |
| Breadboard | 1 | 830 points | Prototyping |
| Jumper Wires | 20+ | Male-to-male | Connections |
| Power Supply | 1 | 5V 2A | External power |
| USB Cable | 1 | Micro USB | Programming |

### Optional Components
- ESP32-CAM module for built-in camera
- LCD Display (16x2 I2C) for status display
- Buzzer for audio feedback
- RFID reader for backup authentication

### Pin Configuration

```
ESP32 Pin       Component
─────────────────────────────────
GPIO 13    →    Entry PIR OUT
GPIO 14    →    Exit PIR OUT
GPIO 15    →    Servo Signal
GPIO 2     →    Green LED (+ via 220Ω)
GPIO 4     →    Red LED (+ via 220Ω)
GND        →    Common Ground
VIN (5V)   →    PIR Sensors VCC
```

## 💻 Software Requirements

### Server (Python)
- Python 3.8 or higher
- OpenCV (`opencv-python`)
- PyTorch (`torch`, `torchvision`)
- EasyOCR (`easyocr`)
- FastAPI (`fastapi`)
- Uvicorn (`uvicorn`)
- SQLite3 (built-in)

### ESP32 (Arduino/ESP-IDF)
- Arduino IDE 2.0+ or ESP-IDF 5.0+
- ESP32 Board Support
- ESP32Servo library
- ArduinoJson library (v6.x or v7.x)

### Development Tools
- Git
- Python virtual environment
- Arduino IDE or PlatformIO

## 📥 Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/esp32-smart-parking.git
cd esp32-smart-parking
```

### 2. Server Setup (Python)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create required directories
mkdir preloaded_images

# Initialize database
python db_setup.py
```

### 3. ESP32 Setup (Arduino IDE)

```bash
# Install Arduino IDE from https://www.arduino.cc/en/software

# Add ESP32 Board Support:
# File → Preferences → Additional Board Manager URLs:
# https://dl.espressif.com/dl/package_esp32_index.json

# Tools → Board → Boards Manager → Install "esp32"

# Install Libraries:
# Tools → Manage Libraries:
# - ESP32Servo by Kevin Harrington
# - ArduinoJson by Benoit Blanchon

# Open esp32_parking/esp32_parking.ino
# Update WiFi credentials and server IP
# Upload to ESP32
```

## ⚙️ Configuration

### Server Configuration

Edit `server.py`:

```python
# Image source directory
IMAGE_DIR = "preloaded_images"

# Camera settings
WEBCAM_INDEX = 0                          # Webcam device index
WIFICAM_URL = "http://192.168.1.50:8080" # WiFi camera URL

# Database path
DB_PATH = "parking_system.db"
```

### ESP32 Configuration

Edit ESP32 code:

```cpp
// WiFi Credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Server URL (your computer's IP)
const char* serverURL = "http://192.168.1.100:8000";

// Pin Definitions (customize if needed)
#define PIR_ENTRY_PIN 13
#define PIR_EXIT_PIN  14
#define SERVO_PIN     15
#define LED_GREEN     2
#define LED_RED       4
```

### Add Registered Vehicles

```bash
# Using Python script
python add_vehicle.py

# Or directly via SQL
sqlite3 parking_system.db
INSERT INTO registered_vehicles(plate, owner) VALUES ('TN88F4089', 'John Doe');
```

## 🚀 Usage

### Starting the System

#### 1. Start the Server

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run server
python server.py

# Server will start on http://0.0.0.0:8000
```

#### 2. Power Up ESP32

Connect ESP32 to power. It will:
- Connect to WiFi
- Initialize sensors and servo
- Start monitoring PIR sensors

#### 3. Monitor System

Open Serial Monitor in Arduino IDE (115200 baud) to see logs:

```
WiFi connected!
IP address: 192.168.1.XXX
ESP32 Parking System Ready!
```

### Entry Process

1. **Vehicle approaches entry gate**
2. **PIR sensor triggers** detection
3. **ESP32 captures image** (or uses preloaded)
4. **Server processes:**
   - Detects license plate region
   - Performs OCR
   - Validates plate format
   - Checks database
5. **If authorized:**
   - ✅ Green LED turns on
   - 🚪 Gate opens (90°)
   - 🅿️ Parking slot allocated
   - ⏱️ Gate closes after 5 seconds
6. **If not authorized:**
   - ❌ Red LED blinks 3 times
   - 🚪 Gate remains closed

### Exit Process

1. **Vehicle approaches exit gate**
2. **PIR sensor triggers** detection
3. **ESP32 captures image**
4. **Server processes:**
   - Detects and reads plate
   - Finds active parking record
   - Frees parking slot
5. **Confirmation:**
   - ✅ Green LED blinks twice
   - 📊 Database updated

## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Entry Request
```http
POST /api/entry_request
Content-Type: application/json

{
  "capture_mode": "preloaded",  // or "webcam" or "wificam"
  "image_name": "test1.jpg"     // required for preloaded mode
}
```

**Response (Authorized):**
```json
{
  "authorized": true,
  "plate": "TN88F4089",
  "slot": "A1"
}
```

**Response (Not Authorized):**
```json
{
  "authorized": false,
  "plate": "XYZ1234",
  "reason": "not_registered"
}
```

#### 2. Exit Request
```http
POST /api/exit_request
Content-Type: application/json

{
  "capture_mode": "preloaded",
  "image_name": "test1.jpg"
}
```

**Response:**
```json
{
  "success": true,
  "plate": "TN88F4089",
  "slot": "A1"
}
```

#### 3. Get All Slots
```http
GET /api/slots
```

**Response:**
```json
{
  "slots": [
    {"slot_label": "A1", "occupied": 1},
    {"slot_label": "A2", "occupied": 0},
    {"slot_label": "A3", "occupied": 0}
  ]
}
```

#### 4. Get Active Parking
```http
GET /api/active_parking
```

**Response:**
```json
{
  "active": [
    {
      "plate": "TN88F4089",
      "slot": "A1",
      "entry_time": "Mon Oct 07 14:30:22 2025"
    }
  ]
}
```

#### 5. Get Events Log
```http
GET /api/events?limit=50
```

**Response:**
```json
{
  "events": [
    {
      "timestamp": "Mon Oct 07 14:35:10 2025",
      "plate": "TN88F4089",
      "authorized": true,
      "event_type": "exit"
    },
    {
      "timestamp": "Mon Oct 07 14:30:22 2025",
      "plate": "TN88F4089",
      "authorized": true,
      "event_type": "entry"
    }
  ]
}
```

#### 6. Update Slot Status
```http
POST /api/slot_update
Content-Type: application/json

{
  "slot_label": "A1",
  "occupied": 0  // 0=free, 1=occupied
}
```

**Response:**
```json
{
  "status": "ok"
}
```

## 📁 Project Structure

```
esp32-smart-parking/
│
├── server.py                    # Main FastAPI server
├── improved_model.py            # Enhanced license plate detection
├── model.py                     # Original detection model
├── db_setup.py                  # Database initialization
├── add_vehicle.py               # Script to add vehicles
├── test_improved_model.py       # Model testing script
├── migrate_db.py                # Database migration
│
├── esp32_parking/               # Arduino/ESP-IDF code
│   ├── esp32_parking.ino        # Arduino code
│   └── main.c                   # ESP-IDF code (alternative)
│
├── preloaded_images/            # Test images directory
│   ├── test1.jpg
│   └── test2.jpg
│
├── parking_system.db            # SQLite database (generated)
│
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── LICENSE                      # License file
└── .gitignore                   # Git ignore rules
```

## 🔧 Troubleshooting

### Common Issues

#### ESP32 Won't Connect to WiFi
- ✅ Check SSID and password (case-sensitive)
- ✅ Ensure using 2.4GHz WiFi (ESP32 doesn't support 5GHz)
- ✅ Move ESP32 closer to router
- ✅ Check serial monitor for error messages

#### Server Connection Failed
```
Error: connection refused
```
**Solutions:**
- Verify server is running: `python server.py`
- Check firewall allows port 8000
- Verify IP address matches in ESP32 code
- Test in browser: `http://YOUR_IP:8000/api/slots`

#### Plate Not Detected
```
"reason": "plate_not_found"
```
**Solutions:**
- Improve image quality (lighting, focus, resolution)
- Check test image exists in `preloaded_images/`
- Verify plate is clearly visible in image
- Try running `python test_improved_model.py` to debug

#### Wrong Plate Number
```
Detected: TNBBF1ND4089
Expected: TN88F4089
```
**Solutions:**
- Model is reading extra text (IND, car brands)
- Use `improved_model.py` (filters false readings)
- Adjust preprocessing parameters
- Consider training custom YOLO model

#### Servo Doesn't Move
- ✅ Check servo power (use external 5V supply)
- ✅ Verify signal wire connected to GPIO 15
- ✅ Test servo separately
- ✅ Add capacitor across servo power

#### PIR Always Triggering
- ✅ Adjust sensitivity potentiometer (turn counter-clockwise)
- ✅ Shield from sunlight/heat sources
- ✅ Increase debounce delay in code

### Debug Mode

Enable detailed logging:

```python
# In server.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

```cpp
// In ESP32 code
Serial.setDebugOutput(true);
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add comments for complex logic
- Test thoroughly before submitting
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👏 Acknowledgments

- **EasyOCR** - OCR engine for license plate reading
- **FastAPI** - Modern web framework for Python
- **ESP32 Community** - Hardware support and libraries
- **OpenCV** - Computer vision library

