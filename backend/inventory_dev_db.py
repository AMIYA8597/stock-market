import sqlite3
import json

def analyze_db():
    conn = sqlite3.connect('dev.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    result = {}
    for table in tables:
        cursor.execute(f"SELECT count(*) FROM {table}")
        count = cursor.fetchone()[0]
        result[table] = count
    
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    analyze_db()
