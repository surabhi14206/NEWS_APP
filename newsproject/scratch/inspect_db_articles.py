import sqlite3
import os

db_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\db.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get count of total news articles
cursor.execute("SELECT COUNT(*) FROM newsfeeds_newsarticle")
total = cursor.fetchone()[0]
print(f"Total NewsArticles in DB: {total}")

# Get count of relevant vs irrelevant
cursor.execute("SELECT is_relevant, COUNT(*) FROM newsfeeds_newsarticle GROUP BY is_relevant")
print("By relevance:", cursor.fetchall())

# Get distinct sources
cursor.execute("SELECT source, COUNT(*) FROM newsfeeds_newsarticle GROUP BY source")
print("By source:", cursor.fetchall())

# Get date range
cursor.execute("SELECT MIN(published_date), MAX(published_date) FROM newsfeeds_newsarticle")
print("Date range in DB:", cursor.fetchone())

# Get latest 10 articles
cursor.execute("SELECT id, title, published_date, is_relevant, source FROM newsfeeds_newsarticle ORDER BY published_date DESC LIMIT 10")
print("\nLATEST 10 ARTICLES:")
for r in cursor.fetchall():
    print(r)

conn.close()
