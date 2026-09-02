from backend.db import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("ALTER TABLE doc_chunks ADD COLUMN IF NOT EXISTS source_file TEXT;")
cur.execute("ALTER TABLE doc_chunks ADD COLUMN IF NOT EXISTS page_number INTEGER;")

conn.commit()
cur.close()
conn.close()

print("Columns added successfully!")