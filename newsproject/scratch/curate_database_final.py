import docx
import re
import sqlite3
import sys

sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")

db_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\db.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

filtered_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\Docs_DB\Indian_Economy_News_Report_Filtered_15Jun2026.docx"
filt_doc = docx.Document(filtered_path)

# Extract table data from filtered document
# Table headers: Date, Source, Article Title, Sector, Impact
table_articles = []
for row in filt_doc.tables[0].rows[1:]:
    date = row.cells[0].text.strip()
    source = row.cells[1].text.strip()
    title = row.cells[2].text.strip()
    sector = row.cells[3].text.strip()
    impact = row.cells[4].text.strip()
    table_articles.append({
        "title": title,
        "sector": sector,
        "impact": impact.lower(),
        "source": source
    })

print(f"Loaded {len(table_articles)} articles from filtered doc table")

# 1. Update/Verify articles in the filtered table
# Since we have duplicates for "Oil prices fall...", we'll handle that title specially.
for art in table_articles:
    title = art['title']
    sector = art['sector']
    direction = art['impact']
    
    # Check if duplicate title exists in DB
    cursor.execute("SELECT id, title, direction FROM newsfeeds_newsarticle WHERE title = ?", (title,))
    db_res = cursor.fetchall()
    
    if len(db_res) > 1:
        # If duplicate, make sure the one matching the specified direction is relevant, and the other is not
        print(f"Duplicate found for title: {title}")
        for db_id, db_title, db_dir in db_res:
            if db_dir.lower() == direction:
                cursor.execute("""
                    UPDATE newsfeeds_newsarticle 
                    SET is_relevant = 1, sector = ?, direction = ?
                    WHERE id = ?
                """, (sector, direction, db_id))
                print(f"  Keep ID {db_id} as relevant ({db_dir})")
            else:
                cursor.execute("""
                    UPDATE newsfeeds_newsarticle 
                    SET is_relevant = 0
                    WHERE id = ?
                """, (db_id,))
                print(f"  Hide ID {db_id} as irrelevant ({db_dir})")
    elif len(db_res) == 1:
        db_id = db_res[0][0]
        cursor.execute("""
            UPDATE newsfeeds_newsarticle 
            SET is_relevant = 1, sector = ?, direction = ?
            WHERE id = ?
        """, (sector, direction, db_id))
    else:
        # Try fuzzy match
        cursor.execute("SELECT id, title FROM newsfeeds_newsarticle WHERE title LIKE ?", (f'%{title[:30]}%',))
        fuzzy_res = cursor.fetchall()
        if fuzzy_res:
            db_id = fuzzy_res[0][0]
            cursor.execute("""
                UPDATE newsfeeds_newsarticle 
                SET is_relevant = 1, sector = ?, direction = ?
                WHERE id = ?
            """, (sector, direction, db_id))
            print(f"Fuzzy updated: {title} -> DB ID {db_id}")
        else:
            print(f"ERROR: Article not found in DB: {title}")

# 2. Add other high-signal articles that are relevant
# E.g. TCS enterprise AI scaling, seafarers missing/killed, El Nino, etc.
other_relevant_titles = [
    "India's TCS partners with Anthropic to drive enterprise AI scaling - Reuters",
    "El Nino declared, all eyes now on monsoon march in India",
    "Mint Explainer | What a strong El Nino could mean for India",
    "India falls out of EM index top 10 for first time in 26 years—What that means & why it matters",
    "Rubio defends US blockade after EAM Jaishankar protests seafarers’ deaths",
    "“Be ready to respond”: India on highest alert, monitoring Hormuz after 3 seafarers killed in US strike",
    "MT Marivex, Settebello, MT Jalveer: All about 3 vessels with Indian crew struck by US near Oman",
    "“Failed to comply with directions”: US on why it attacked 3 vessels carrying Indian crew",
    "Three Indian seafarers missing after US strike on tanker off Oman - Reuters",
    "In touch with India: US after summons to diplomat, attack on tanker off Oman",
    "India top priority for France ahead of G7 Summit; focus on West Asia and strategic defence ties",
    "COVID-19 forced vulnerable Indian households into ‘impossible choices’: Study",
    "Sri Lanka has reduced the export tariff on IT Services,",
    "Bangladesh cuts government exports tariff by 8% - effective june 2026,",
    "Wall Street IPO Boom Leaves India’s Fighting for Attention",
    "Bangladesh Targets Growth Revival With Record Budget Spending",
]

for title in other_relevant_titles:
    # Set them as relevant in DB
    cursor.execute("SELECT id FROM newsfeeds_newsarticle WHERE title = ?", (title,))
    db_res = cursor.fetchall()
    if db_res:
        for (db_id,) in db_res:
            cursor.execute("UPDATE newsfeeds_newsarticle SET is_relevant = 1 WHERE id = ?", (db_id,))
    else:
        # Fuzzy match
        clean_t = title.replace('—', ' ').replace('“', '').replace('”', '').replace('’', "'")
        cursor.execute("SELECT id FROM newsfeeds_newsarticle WHERE title LIKE ?", (f'%{clean_t[:30]}%',))
        fuzzy_res = cursor.fetchall()
        if fuzzy_res:
            for (db_id,) in fuzzy_res:
                cursor.execute("UPDATE newsfeeds_newsarticle SET is_relevant = 1 WHERE id = ?", (db_id,))
                print(f"Set relevant (fuzzy) for: {title}")
        else:
            print(f"WARNING: Other relevant article not found in DB: {title}")

# 3. Clean up the misclassifications and mark them as irrelevant
# - Road accident deaths: sector = 'Road Transport', event_class = 'Safety and Regulation'
# - Hauz Rani B&B fire: sector = 'Local Administration', event_class = 'Safety and Regulation'
# - Great Nicobar's Past: sector = 'History and Heritage', event_class = 'General News'
misclassified_corrections = [
    {
        "title_like": "%road accident deaths%",
        "sector": "Road Transport",
        "event_class": "Safety and Regulation",
        "is_relevant": 0
    },
    {
        "title_like": "%fire inspection%",
        "sector": "Local Administration",
        "event_class": "Safety and Regulation",
        "is_relevant": 0
    },
    {
        "title_like": "%Nicobar%",
        "sector": "History and Heritage",
        "event_class": "General News",
        "is_relevant": 0
    }
]

for corr in misclassified_corrections:
    cursor.execute("""
        UPDATE newsfeeds_newsarticle 
        SET sector = ?, event_class = ?, is_relevant = ?
        WHERE title LIKE ?
    """, (corr['sector'], corr['event_class'], corr['is_relevant'], corr['title_like']))
    print(f"Updated misclassification matching {corr['title_like']}")

# 4. Hide all other articles in the timeframe (June 8 to June 15) that are not in our kept list
# Find all articles in timeframe
cursor.execute("""
    SELECT id, title 
    FROM newsfeeds_newsarticle 
    WHERE published_date >= '2026-06-08 00:00:00' 
      AND published_date <= '2026-06-15 23:59:59'
""")
all_timeframe = cursor.fetchall()

# Determine which ones to set as irrelevant (if they are not in the table or the other_relevant lists)
kept_ids = set()
# Get IDs of articles in filtered table
for art in table_articles:
    title = art['title']
    cursor.execute("SELECT id FROM newsfeeds_newsarticle WHERE title = ?", (title,))
    res = cursor.fetchall()
    for (r_id,) in res:
        # Deduplication check
        cursor.execute("SELECT direction FROM newsfeeds_newsarticle WHERE id = ?", (r_id,))
        r_dir = cursor.fetchone()[0]
        if r_dir.lower() == art['impact']:
            kept_ids.add(r_id)

# Get IDs of other relevant articles
for title in other_relevant_titles:
    cursor.execute("SELECT id FROM newsfeeds_newsarticle WHERE title = ?", (title,))
    res = cursor.fetchall()
    for (r_id,) in res:
        kept_ids.add(r_id)
    # Also fuzzy match IDs
    clean_t = title.replace('—', ' ').replace('“', '').replace('”', '').replace('’', "'")
    cursor.execute("SELECT id FROM newsfeeds_newsarticle WHERE title LIKE ?", (f'%{clean_t[:30]}%',))
    res = cursor.fetchall()
    for (r_id,) in res:
        kept_ids.add(r_id)

print(f"Number of kept IDs: {len(kept_ids)}")

# Hide everything else in timeframe
hidden_count = 0
for db_id, title in all_timeframe:
    if db_id not in kept_ids:
        cursor.execute("UPDATE newsfeeds_newsarticle SET is_relevant = 0 WHERE id = ?", (db_id,))
        hidden_count += 1

print(f"Marked {hidden_count} articles as irrelevant (hidden) in the timeframe.")

# Let's count how many are now relevant in the timeframe
cursor.execute("""
    SELECT COUNT(*) 
    FROM newsfeeds_newsarticle 
    WHERE is_relevant = 1
      AND published_date >= '2026-06-08 00:00:00' 
      AND published_date <= '2026-06-15 23:59:59'
""")
relevant_now = cursor.fetchone()[0]
print(f"Relevant articles in timeframe now: {relevant_now}")

conn.commit()
conn.close()
