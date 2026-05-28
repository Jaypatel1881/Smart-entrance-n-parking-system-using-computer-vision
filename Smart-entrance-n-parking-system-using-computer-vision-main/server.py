# server.py
import os
import sqlite3
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import cv2
from improved_model import ImprovedPlateDetectorOCR

# config
IMAGE_DIR = "preloaded_images"   # put test images here
WEBCAM_INDEX = 0                 # set to your webcam index
WIFICAM_URL = None               # or "rtsp://..." or "http://ip:port/stream"
DB_PATH = "parking_system.db"

detector = ImprovedPlateDetectorOCR(model_path="custom_plate_model.pth")
app = FastAPI()

# DB helpers
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS registered_vehicles(
        id INTEGER PRIMARY KEY,
        plate TEXT UNIQUE,
        owner TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS parking_slots(
        id INTEGER PRIMARY KEY,
        slot_label TEXT UNIQUE,
        occupied INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS active_parking(
        id INTEGER PRIMARY KEY,
        plate TEXT,
        slot_label TEXT,
        entry_time TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS events_log(
        id INTEGER PRIMARY KEY,
        timestamp TEXT,
        plate TEXT,
        authorized INTEGER,
        image_path TEXT
    )""")
    # Add event_type column if it doesn't exist (for backward compatibility)
    c.execute("PRAGMA table_info(events_log)")
    columns = [row[1] for row in c.fetchall()]
    if 'event_type' not in columns:
        c.execute("ALTER TABLE events_log ADD COLUMN event_type TEXT DEFAULT 'entry'")
    # create slots example if empty
    c.execute("SELECT COUNT(*) FROM parking_slots")
    if c.fetchone()[0] == 0:
        slots = [("A1",0),("A2",0),("A3",0),("B1",0)]
        c.executemany("INSERT INTO parking_slots(slot_label,occupied) VALUES (?,?)", slots)
    conn.commit()
    conn.close()

init_db()

# Pydantic models
class EntryRequest(BaseModel):
    capture_mode: Optional[str] = "preloaded"  # default to preloaded
    image_name: Optional[str] = None          # required for preloaded
    camera_index: Optional[int] = WEBCAM_INDEX
    cam_url: Optional[str] = WIFICAM_URL

class SlotUpdate(BaseModel):
    slot_label: str
    occupied: int   # 0 or 1

# utility functions
def capture_image(req: EntryRequest):
    if req.capture_mode == "preloaded":
        if not req.image_name:
            raise ValueError("image_name required for preloaded mode")
        path = os.path.join(IMAGE_DIR, req.image_name)
        if not os.path.exists(path):
            raise FileNotFoundError("preloaded image not found")
        img = cv2.imread(path)
        return img, path
    elif req.capture_mode == "webcam":
        cap = cv2.VideoCapture(req.camera_index)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError("webcam not available")
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError("webcam capture failed")
        return frame, None
    elif req.capture_mode == "wificam":
        if not req.cam_url:
            raise ValueError("cam_url required for wificam")
        cap = cv2.VideoCapture(req.cam_url)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError("wificam not available")
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError("wificam capture failed")
        return frame, None
    else:
        raise ValueError("invalid capture_mode")

def query_registered(plate):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM registered_vehicles WHERE plate=?", (plate,))
    res = c.fetchone()
    conn.close()
    return res is not None

def allocate_slot(plate):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # pick first free slot
    c.execute("SELECT slot_label FROM parking_slots WHERE occupied=0 LIMIT 1")
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    slot = row[0]
    # mark occupied
    c.execute("UPDATE parking_slots SET occupied=1 WHERE slot_label=?", (slot,))
    c.execute("INSERT INTO active_parking(plate, slot_label, entry_time) VALUES (?,?,?)", (plate,slot,time.ctime()))
    conn.commit()
    conn.close()
    return slot

def log_event(plate, authorized, image_path=None, event_type='entry'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO events_log(timestamp,plate,authorized,image_path,event_type) VALUES (?,?,?,?,?)", 
              (time.ctime(), plate, int(bool(authorized)), image_path, event_type))
    conn.commit()
    conn.close()

@app.post("/api/entry_request")
def entry_request(req: EntryRequest):
    """
    Called by ESP32 when PIR at gate detects vehicle.
    Body example:
      { "capture_mode": "preloaded", "image_name": "test1.jpg" }
    """
    try:
        img, path = capture_image(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # run improved detector+ocr
    results = detector.detect_and_ocr(img)  # list of (box, text)
    
    # Get best plate from results (already cleaned by improved model)
    best_plate = ""
    if results:
        # Results are already cleaned, just pick the first one
        best_plate = results[0][1]
    
    # Fallback: if nothing detected, try full-image OCR with cleaning
    if not best_plate:
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            full = detector.reader.readtext(gray)
            if full:
                # Combine all text and clean it
                combined_text = "".join([r[1] for r in full])
                best_plate = detector.clean_plate_text(combined_text)
        except Exception as e:
            print(f"[ERROR] Fallback OCR failed: {e}")

    if not best_plate:
        log_event(None, False, path, 'entry')
        return {"authorized": False, "reason": "plate_not_found", "plate": None}

    print(f"[ENTRY] Detected plate: {best_plate}")

    # check db
    is_registered = query_registered(best_plate)
    if is_registered:
        slot = allocate_slot(best_plate)
        if not slot:
            log_event(best_plate, False, path, 'entry')
            return {"authorized": False, "plate": best_plate, "reason": "no_slots_available"}
        log_event(best_plate, True, path, 'entry')
        return {"authorized": True, "plate": best_plate, "slot": slot}
    else:
        log_event(best_plate, False, path, 'entry')
        return {"authorized": False, "plate": best_plate, "reason": "not_registered"}

@app.post("/api/exit_request")
def exit_request(req: EntryRequest):
    """
    Called by ESP32 when PIR at exit gate detects vehicle.
    Captures image, detects plate, finds matching active parking, and frees slot.
    """
    try:
        img, path = capture_image(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # run improved detector+ocr
    results = detector.detect_and_ocr(img)
    
    # Get best plate from results
    best_plate = ""
    if results:
        best_plate = results[0][1]
    
    # Fallback: if nothing detected, try full-image OCR with cleaning
    if not best_plate:
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            full = detector.reader.readtext(gray)
            if full:
                combined_text = "".join([r[1] for r in full])
                best_plate = detector.clean_plate_text(combined_text)
        except Exception as e:
            print(f"[ERROR] Fallback OCR failed: {e}")

    if not best_plate:
        log_event(None, False, path, 'exit')
        return {"success": False, "reason": "plate_not_found", "plate": None}

    print(f"[EXIT] Detected plate: {best_plate}")

    # Find active parking for this plate
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT slot_label FROM active_parking WHERE plate=?", (best_plate,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        log_event(best_plate, False, path, 'exit')
        return {"success": False, "reason": "no_active_parking", "plate": best_plate}
    
    slot = row[0]
    
    # Free the slot
    c.execute("UPDATE parking_slots SET occupied=0 WHERE slot_label=?", (slot,))
    c.execute("DELETE FROM active_parking WHERE plate=?", (best_plate,))
    
    conn.commit()
    conn.close()
    
    log_event(best_plate, True, path, 'exit')
    
    return {"success": True, "plate": best_plate, "slot": slot}

@app.post("/api/slot_update")
def slot_update(s: SlotUpdate):
    """
    Called by ESP32 when vehicle exits.
    Marks slot as free and removes from active_parking.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Update slot status
    c.execute("UPDATE parking_slots SET occupied=? WHERE slot_label=?", (s.occupied, s.slot_label))
    
    # If marking as free, remove from active_parking and log exit
    if s.occupied == 0:
        c.execute("SELECT plate FROM active_parking WHERE slot_label=?", (s.slot_label,))
        row = c.fetchone()
        if row:
            plate = row[0]
            c.execute("DELETE FROM active_parking WHERE slot_label=?", (s.slot_label,))
            # Log exit event
            c.execute("INSERT INTO events_log(timestamp,plate,authorized,image_path,event_type) VALUES (?,?,?,?,?)",
                     (time.ctime(), plate, 1, None, 'exit'))
    
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/slots")
def get_slots():
    """Get all parking slots status"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT slot_label, occupied FROM parking_slots")
    rows = c.fetchall()
    conn.close()
    return {"slots": [{"slot_label": r[0], "occupied": r[1]} for r in rows]}

@app.get("/api/active_parking")
def get_active_parking():
    """Get all currently parked vehicles"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT plate, slot_label, entry_time FROM active_parking")
    rows = c.fetchall()
    conn.close()
    return {"active": [{"plate": r[0], "slot": r[1], "entry_time": r[2]} for r in rows]}

@app.get("/api/events")
def get_events(limit: int = 50):
    """Get recent events log"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT timestamp, plate, authorized, event_type FROM events_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return {"events": [{"timestamp": r[0], "plate": r[1], "authorized": bool(r[2]), "event_type": r[3]} for r in rows]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)