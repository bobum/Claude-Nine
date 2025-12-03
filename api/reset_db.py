import sqlite3
conn = sqlite3.connect('claude_nine.db')
conn.execute("UPDATE work_items SET status = 'queued', started_at = NULL, completed_at = NULL")
conn.commit()
print('Reset all work items to queued')
conn.close()
