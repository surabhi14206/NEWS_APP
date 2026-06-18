import docx
import sqlite3
import sys

sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")

db_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\db.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

doc_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\Docs_DB\docs_7_Days.docx"
doc = docx.Document(doc_path)

print("ID, Title, Source, Date, DB_ID, Is_Relevant")
unmatched_count = 0
for idx, row in enumerate(doc.tables[0].rows[1:]):
    date_src = row.cells[0].text.strip()
    title = row.cells[1].text.strip()
    
    # Try to find in DB
    cursor.execute("SELECT id, is_relevant, sector, event_class, direction FROM newsfeeds_newsarticle WHERE title = ?", (title,))
    db_res = cursor.fetchall()
    if db_res:
        db_id, is_rel, sec, ev, dir_val = db_res[0]
        # If there are duplicates in DB
        db_ids = [str(r[0]) for r in db_res]
        print(f"{idx+1}: {title} | DB_IDs: {', '.join(db_ids)} | Is_Relevant: {[r[1] for r in db_res]}")
    else:
        # Try fuzzy match
        cursor.execute("SELECT id, is_relevant, title FROM newsfeeds_newsarticle WHERE title LIKE ?", (f'%{title[:30]}%',))
        db_res = cursor.fetchall()
        if db_res:
            db_ids = [str(r[0]) for r in db_res]
            print(f"{idx+1} (FUZZY): {title} | Matches: {db_res[0][2][:40]} | DB_IDs: {', '.join(db_ids)}")
        else:
            print(f"{idx+1} (UNMATCHED): {title}")
            unmatched_count += 1

print("Total unmatched in DB:", unmatched_count)
conn.close()
