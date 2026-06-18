import sqlite3
import sys

sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")

db_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\db.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT direction, COUNT(*) 
    FROM newsfeeds_newsarticle 
    WHERE is_relevant = 1
      AND published_date >= '2026-06-08 00:00:00' 
      AND published_date <= '2026-06-15 23:59:59'
    GROUP BY direction
""")
print("Sentiments count in DB:")
for r in cursor.fetchall():
    print(r)

# List all relevant articles
cursor.execute("""
    SELECT id, title, direction 
    FROM newsfeeds_newsarticle 
    WHERE is_relevant = 1
      AND published_date >= '2026-06-08 00:00:00' 
      AND published_date <= '2026-06-15 23:59:59'
    ORDER BY published_date DESC
""")
print("\nALL RELEVANT ARTICLES IN TIMEFRAME:")
for idx, r in enumerate(cursor.fetchall()):
    print(f"{idx+1}: ID {r[0]} | [{r[2].upper()}] {r[1]}")

conn.close()
