import sqlite3
import os
import sys

sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")

db_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\db.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

keywords = ["TCS", "Anthropic", "Airbus", "Oman", "monsoon", "Razorpay", "France", "Jaishankar", "Tata", "Airbus"]

for kw in keywords:
    cursor.execute("""
        SELECT id, title, published_date, is_relevant, source 
        FROM newsfeeds_newsarticle 
        WHERE (title LIKE ? OR description LIKE ?)
          AND published_date >= '2026-06-08 00:00:00' 
          AND published_date <= '2026-06-15 23:59:59'
    """, (f'%{kw}%', f'%{kw}%'))
    res = cursor.fetchall()
    print(f"\nKeyword '{kw}' matches ({len(res)}):")
    for r in res:
        print(r)

conn.close()
