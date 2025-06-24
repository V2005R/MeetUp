#!/bin/bash
python -c "
import sqlite3
conn = sqlite3.connect('meetings.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS meetings (
        id TEXT PRIMARY KEY,
        host_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id TEXT,
        name TEXT,
        is_host BOOLEAN,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (meeting_id) REFERENCES meetings(id)
    )
''')
conn.commit()
conn.close()
print('Database initialized successfully')
"
