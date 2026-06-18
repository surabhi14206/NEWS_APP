import docx
import re
import sqlite3
import json
import sys
import os

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
conn.commit()
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
    cursor.execute("SELECT id, title, direction FROM newsfeeds_newsarticle WHERE title = ?", (title_str,))
    res = cursor.fetchall()
    if not res:
        # Try fuzzy match
        cursor.execute("SELECT id, title, direction FROM newsfeeds_newsarticle WHERE title LIKE ?", (f'%{title_str[:30]}%',))
        res = cursor.fetchall()
    
    ids = []
    for r_id, r_title, r_dir in res:
        if impact_str:
            if r_dir.lower() == impact_str:
                ids.append(r_id)
        else:
            ids.append(r_id)
    return ids

# 2. Gather IDs from filtered table and update their sector/impact
for art in table_articles:
    title = art['title']
    direction = art['impact']
    sector = art['sector']
    
    matching_ids = find_article_ids(title, direction)
    if not matching_ids:
        matching_ids = find_article_ids(title)
        
    for r_id in matching_ids:
        kept_ids.add(r_id)
        cursor.execute("""
            UPDATE newsfeeds_newsarticle 
            SET is_relevant = 1, sector = ?, direction = ?
            WHERE id = ?
        """, (sector, direction, r_id))

print(f"Gathered {len(kept_ids)} IDs from filtered table")

# 3. Gather other relevant articles to hit exactly 52
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
    
    # 3 additional high-signal oil/Hormuz articles to make it exactly 52
    "Hormuz Oil Flows Surge as Gulf Producers Embrace Workarounds",
    "OPEC again lowers 2026 global oil demand growth forecast - Reuters",
    "Oil falls as traders digest escalation in US-Iran strikes - Reuters"
]

for title in other_relevant_titles:
    matching_ids = find_article_ids(title)
    for r_id in matching_ids:
        kept_ids.add(r_id)
        cursor.execute("UPDATE newsfeeds_newsarticle SET is_relevant = 1 WHERE id = ?", (r_id,))

print(f"Total kept IDs including other relevant: {len(kept_ids)}")

# 4. Hide other articles in timeframe and dump them to no_use_data.json
cursor.execute("""
    SELECT id, title, description, event_class, sub_type, sector, channel, summary, direction, direction_reason, impact_score, origin, published_date, source, link 
    FROM newsfeeds_newsarticle 
    WHERE published_date >= '2026-06-08 00:00:00' 
      AND published_date <= '2026-06-15 23:59:59'
""")
all_timeframe = cursor.fetchall()

no_use_list = []
hidden_count = 0

for item in all_timeframe:
    db_id = item[0]
    title = item[1]
    
    if db_id not in kept_ids:
        cursor.execute("UPDATE newsfeeds_newsarticle SET is_relevant = 0 WHERE id = ?", (db_id,))
        hidden_count += 1
        
        # Check for the misclassified corrections to fix classifications even in no_use_data.json
        sector_val = item[5]
        event_class_val = item[3]
        
        if "road accident deaths" in title.lower():
            sector_val = "Road Transport"
            event_class_val = "Safety and Regulation"
        elif "fire inspection" in title.lower():
            sector_val = "Local Administration"
            event_class_val = "Safety and Regulation"
        elif "nicobar" in title.lower():
            sector_val = "History and Heritage"
            event_class_val = "General News"
            
        no_use_list.append({
            "title": title,
            "description": item[2],
            "is_relevant": False,
            "event_class": event_class_val,
            "sub_type": item[4],
            "sector": sector_val,
            "channel": item[6],
            "insights": item[7],
            "summary": item[7],
            "direction": item[8],
            "direction_reason": item[9],
            "impact_score": item[10],
            "origin": item[11],
            "published_date": item[12],
            "source": item[13],
            "link": item[14],
            "economic_note": "This event has low or no macroeconomic relevance to the Indian economy. It is either a competitor trade policy, generic central bank news, or a local incident with negligible macroeconomic transmission."
        })

# Save to no_use_data.json
no_use_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\ML_Operation_Test_Train\no_use_data.json"
with open(no_use_path, 'w', encoding='utf-8') as f:
    json.dump(no_use_list, f, indent=2)

print(f"Marked {hidden_count} articles as irrelevant (hidden) in the timeframe.")
print(f"Dumped {len(no_use_list)} irrelevant articles to {no_use_path}")

# 5. Correct classifications in database for misclassified ones (and make sure they are is_relevant=0)
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

# 6. Check count of relevant articles in timeframe
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
