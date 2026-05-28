import sqlite3

DB_PATH = "parking_system.db"

def add_vehicle(plate, owner):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO registered_vehicles (plate, owner) VALUES (?, ?)", (plate.upper(), owner))
        conn.commit()
        print(f"Added {plate} for owner {owner}")
    except sqlite3.IntegrityError:
        print(f"Plate {plate} already exists!")
    finally:
        conn.close()

# Example:
add_vehicle("RJ11CV0002", "hellow")
