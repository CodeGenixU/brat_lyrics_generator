import datetime
import os
import sqlite3
import shutil

# Test Server Organization

print("Step 1: Checking Folders...")
if not os.path.exists("generated_files"):
    print("Creating 'generated_files' (Simulation of server startup)...")
    os.makedirs("generated_files")

print("Step 2: Checking DB...")
if not os.path.exists("generations.db"):
    print("DB not found (normal if server hasn't run), creating dummy...")
    conn = sqlite3.connect("generations.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  song TEXT, artist TEXT, filename TEXT, created_at TIMESTAMP)''')
    conn.commit()
    conn.close()

# Simulate a "Generation" by manually creating files in generated_files/
print("Step 3: Simulating a generation...")
dummy_output = "generated_files/test_video.mp4"
with open(dummy_output, "w") as f:
    f.write("dummy video content")

# Log to DB
print("Step 4: Logging to DB...")
conn = sqlite3.connect("generations.db")
c = conn.cursor()
c.execute("INSERT INTO history (song, artist, filename, created_at) VALUES (?, ?, ?, ?)",
          ("Test Song", "Test Artist", "test_video.mp4", datetime.datetime.now()))
conn.commit()

# Verify DB content
print("Step 5: Verifying DB Record...")
c.execute("SELECT * FROM history ORDER BY id DESC LIMIT 1")
row = c.fetchone()
conn.close()

if row:
    print(f"Success! Found record: {row}")
else:
    print("Error: DB record not found.")
    exit(1)

# Verify File
if os.path.exists(dummy_output):
    print(f"Success! File found in {dummy_output}")
else:
    print(f"Error: File not found in {dummy_output}")
    exit(1)

print("Verification complete.")
