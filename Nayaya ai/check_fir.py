import sqlite3

conn = sqlite3.connect('IndiaLaw.db')
cursor = conn.cursor()

# Count records
cursor.execute('SELECT COUNT(*) FROM fir_records')
count = cursor.fetchone()[0]
print(f'Total FIR records: {count}')

# Show recent records
cursor.execute('SELECT fir_no, fir_date, dist, ps, status FROM fir_records ORDER BY created_at DESC LIMIT 5')
rows = cursor.fetchall()
print('Recent FIR records:')
for row in rows:
    print(row)

conn.close()