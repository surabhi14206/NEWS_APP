import docx
import sqlite3
import sys

sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")

db_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\db.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Restore all articles in the timeframe to is_relevant = 1 first
cursor.execute("""
    UPDATE newsfeeds_newsarticle 
    SET is_relevant = 1 
    WHERE published_date >= '2026-06-08 00:00:00' 
      AND published_date <= '2026-06-15 23:59:59'
""")
print("Restored all articles in timeframe to relevant status")

filtered_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\Docs_DB\Indian_Economy_News_Report_Filtered_15Jun2026.docx"
filt_doc = docx.Document(filtered_path)

# Extract table data
table_articles = []
for row in filt_doc.tables[0].rows[1:]:
    date = row.cells[0].text.strip()
    source = row.cells[1].text.strip()
    title = row.cells[2].text.strip()
    sector = row.cells[3].text.strip()
    impact = row.cells[4].text.strip().lower()
    table_articles.append({
        "title": title,
        "sector": sector,
        "impact": impact,
        "source": source
    })

# Kept IDs set
kept_ids = set()

# Fuzzy search helper
def find_article_ids(title_str, impact_str=None):
    # Try exact match
    cursor.execute("SELECT id, title, direction FROM newsfeeds_newsarticle WHERE title = ?", (title_str,))
    res = cursor.fetchall()
    if not res:
        # Try fuzzy match (prefix 30 chars)
        cursor.execute("SELECT id, title, direction FROM newsfeeds_newsarticle WHERE title LIKE ?", (f'%{title_str[:30]}%',))
        res = cursor.fetchall()
    
    ids = []
    for r_id, r_title, r_dir in res:
        if impact_str:
            # If checking sentiment direction
            if r_dir.lower() == impact_str:
                ids.append(r_id)
        else:
            ids.append(r_id)
    return ids

# 2. Gather IDs from filtered table
for art in table_articles:
    title = art['title']
    direction = art['impact']
    sector = art['sector']
    
    matching_ids = find_article_ids(title, direction)
    if not matching_ids:
        # If direction match failed, try without direction matching
        matching_ids = find_article_ids(title)
        
    for r_id in matching_ids:
        kept_ids.add(r_id)
        # Update sector and direction
        cursor.execute("""
            UPDATE newsfeeds_newsarticle 
            SET is_relevant = 1, sector = ?, direction = ?
            WHERE id = ?
        """, (sector, direction, r_id))

print(f"Gathered {len(kept_ids)} IDs from filtered table")

# 3. Gather other relevant articles
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
    "Delhi, Punjab, Odisha: States roll out free travel for NEET-UG re-exam candidates",
    "Pilots’ body opposes interim report on AI171 crash, demands judicial probe",
    "GE engine review delays final Air India crash report ahead of first anniversary",
    "Air India crash report delay expected due to unfinished engine analysis, source says - Reuters",
    "VIEW CPI rises at fastest rate in three years but meets market expectations - Reuters",
    "COVID-19 forced vulnerable Indian households into ‘impossible choices’: Study"
]

for title in other_relevant_titles:
    matching_ids = find_article_ids(title)
    for r_id in matching_ids:
        kept_ids.add(r_id)
        cursor.execute("UPDATE newsfeeds_newsarticle SET is_relevant = 1 WHERE id = ?", (r_id,))

print(f"Total kept IDs including other relevant: {len(kept_ids)}")

# 4. Hide other articles in timeframe
cursor.execute("""
    SELECT id, title 
    FROM newsfeeds_newsarticle 
    WHERE published_date >= '2026-06-08 00:00:00' 
      AND published_date <= '2026-06-15 23:59:59'
""")
all_timeframe = cursor.fetchall()

hidden_count = 0
for db_id, title in all_timeframe:
    if db_id not in kept_ids:
        cursor.execute("UPDATE newsfeeds_newsarticle SET is_relevant = 0 WHERE id = ?", (db_id,))
        hidden_count += 1

print(f"Marked {hidden_count} articles as irrelevant (hidden) in the timeframe.")

# 5. Check count of relevant articles in timeframe
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
