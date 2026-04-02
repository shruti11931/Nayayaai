import sqlite3

conn = sqlite3.connect('IndiaLaw.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print('Existing tables:', tables)

# Check structure of one table if it exists
if tables:
    table_name = tables[0][0]
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f'Columns in {table_name}:', columns)

conn.close()