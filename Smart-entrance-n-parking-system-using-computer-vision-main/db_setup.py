# db_setup.py
import sqlite3
DB_PATH = "parking_system.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# create tables (same as server.init_db)
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

# CREATE THE MISSING events_log TABLE
c.execute("""CREATE TABLE IF NOT EXISTS events_log(
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    plate TEXT,
    authorized INTEGER,
    image_path TEXT,
    event_type TEXT DEFAULT 'entry'
)""")

# seed example data
c.execute("INSERT OR IGNORE INTO registered_vehicles(plate, owner) VALUES (?, ?)", ("R183JF", "Demo Owner"))
c.execute("INSERT OR IGNORE INTO parking_slots(slot_label, occupied) VALUES (?, ?)", ("A1",0))
c.execute("INSERT OR IGNORE INTO parking_slots(slot_label, occupied) VALUES (?, ?)", ("A2",0))
c.execute("INSERT OR IGNORE INTO parking_slots(slot_label, occupied) VALUES (?, ?)", ("A3",0))
c.execute("INSERT OR IGNORE INTO parking_slots(slot_label, occupied) VALUES (?, ?)", ("B1",0))

conn.commit()
conn.close()
print("DB initialized successfully!")
print("Tables created: registered_vehicles, parking_slots, active_parking, events_log")