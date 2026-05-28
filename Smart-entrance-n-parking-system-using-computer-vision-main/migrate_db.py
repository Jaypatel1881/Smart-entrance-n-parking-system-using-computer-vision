# migrate_db.py
import sqlite3

DB_PATH = "parking_system.db"

def migrate_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Check if event_type column exists
        c.execute("PRAGMA table_info(events_log)")
        columns = [row[1] for row in c.fetchall()]
        
        if 'event_type' not in columns:
            print("Adding event_type column to events_log table...")
            # Add the new column with default value
            c.execute("ALTER TABLE events_log ADD COLUMN event_type TEXT DEFAULT 'entry'")
            conn.commit()
            print("✓ Migration successful! event_type column added.")
        else:
            print("✓ Database already up to date. No migration needed.")
    
    except sqlite3.OperationalError as e:
        print(f"Error during migration: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()