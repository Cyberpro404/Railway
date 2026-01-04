import sqlite3
from pathlib import Path
from datetime import datetime, timezone

db_path = Path('rail.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Clear the corrupted empty data and reset with proper initial state
cursor.execute('DELETE FROM latest WHERE data = "{}"')
cursor.execute('INSERT OR REPLACE INTO latest (id, timestamp, data) VALUES (1, ?, ?)', 
               (datetime.now(timezone.utc).isoformat(), '{}'))
conn.commit()
conn.close()

print('Database cleaned - corrupted empty data removed')
