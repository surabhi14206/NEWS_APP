import sqlite3
import os
import sys

sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")

db_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\db.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Query count between June 8 and June 15
cursor.execute("""
    SELECT COUNT(*) 
    FROM newsfeeds_newsarticle 
    WHERE published_date >= '2026-06-08 00:00:00' 
      AND published_date <= '2026-06-15 23:59:59'
""")
total = cursor.fetchone()[0]
print(f"Total articles between Jun 8 and Jun 15: {total}")

# Breakdown by is_relevant
cursor.execute("""
    SELECT is_relevant, COUNT(*) 
    FROM newsfeeds_newsarticle 
    WHERE published_date >= '2026-06-08 00:00:00' 
      AND published_date <= '2026-06-15 23:59:59'
    GROUP BY is_relevant
""")
print("Breakdown by relevance:", cursor.fetchall())

conn.close()
