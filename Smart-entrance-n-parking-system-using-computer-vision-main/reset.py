import sqlite3

DB_PATH = "parking_system.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# reset all parking slots to unoccupied
c.execute("UPDATE parking_slots SET occupied=0")

# clear active parking
c.execute("DELETE FROM active_parking")

conn.commit()
conn.close()

print("Parking slots reset. All slots are now free.")
