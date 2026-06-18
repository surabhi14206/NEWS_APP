import docx
import sqlite3
import json
import sys

sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")

db_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\db.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

doc_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\Docs_DB\docs_7_Days.docx"
doc = docx.Document(doc_path)

articles = []
for idx, row in enumerate(doc.tables[0].rows[1:]):
    date_src = row.cells[0].text.strip()
    title = row.cells[1].text.strip()
    
    cursor.execute("SELECT id, is_relevant, sector, event_class, direction, direction_reason, impact_score FROM newsfeeds_newsarticle WHERE title = ?", (title,))
    db_res = cursor.fetchall()
    
    if db_res:
        for db_id, is_rel, sec, ev, direction, reason, score in db_res:
            articles.append({
                "index": idx + 1,
                "db_id": db_id,
                "title": title,
                "source": date_src.split('\n')[-1].replace('(', '').replace(')', '') if '\n' in date_src else date_src,
                "date": date_src.split('\n')[0] if '\n' in date_src else date_src,
                "sector": sec,
                "event_class": ev,
                "direction": direction,
                "reason": reason,
                "impact_score": score,
                "is_relevant": is_rel
            })
    else:
        # Fuzzy match
        cursor.execute("SELECT id, is_relevant, sector, event_class, direction, direction_reason, impact_score, title FROM newsfeeds_newsarticle WHERE title LIKE ?", (f'%{title[:30]}%',))
        db_res = cursor.fetchall()
        for db_id, is_rel, sec, ev, direction, reason, score, full_title in db_res:
            articles.append({
                "index": idx + 1,
                "db_id": db_id,
                "title": full_title,
                "source": date_src.split('\n')[-1].replace('(', '').replace(')', '') if '\n' in date_src else date_src,
                "date": date_src.split('\n')[0] if '\n' in date_src else date_src,
                "sector": sec,
                "event_class": ev,
                "direction": direction,
                "reason": reason,
                "impact_score": score,
                "is_relevant": is_rel
            })

with open(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\scratch\all_128_details.json", "w", encoding="utf-8") as f:
    json.dump(articles, f, indent=4)

print("Exported details of", len(articles), "articles")
conn.close()
