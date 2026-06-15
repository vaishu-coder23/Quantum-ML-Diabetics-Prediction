import sqlite3

def migrate(db_path='diabetes_platform.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Checking for 'summary' column in 'prediction_history' table...")
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(prediction_history)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'summary' not in columns:
            print("Adding 'summary' column...")
            cursor.execute("ALTER TABLE prediction_history ADD COLUMN summary TEXT")
            conn.commit()
            print("Migration successful: 'summary' column added.")
        else:
            print("Column 'summary' already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
