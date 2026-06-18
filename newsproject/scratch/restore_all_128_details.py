import json
import re
import os
import sys
import django
from datetime import datetime

# Setup Django settings context
sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.models import NewsArticle, DuplicateNewsArticle
from django.utils.timezone import make_aware

# Load all_128_details.json
with open('scratch/all_128_details.json', 'r', encoding='utf-8') as f:
    details = json.load(f)

# Load log
with open('../newsfeeds_scrape_log.json', 'r', encoding='utf-8') as f:
    log_data = json.load(f)
log_articles = log_data.get('all_articles_log', [])

# Load split datasets as fallback
splits = []
for fpath in ['../ML_Operation_Test_Train/no_use_data.json', '../ML_Operation_Test_Train/low_impact_events.json', '../ML_Operation_Test_Train/test_split.json']:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            splits.extend(json.load(f))
    except Exception:
        pass

def normalize(s):
    return re.sub(r'\W+', '', s.lower().strip())

log_by_title = {normalize(a['title']): a for a in log_articles}
split_by_title = {normalize(a['title']): a for a in splits}

count_added = 0
count_updated = 0
count_errors = 0

for item in details:
    title = item['title']
    norm_title = normalize(title)
    
    # Check if title already exists in DB (exactly or normalized)
    db_res = list(NewsArticle.objects.filter(title=title))
    if not db_res:
        # try normalized check in DB
        for art in NewsArticle.objects.all():
            if normalize(art.title) == norm_title:
                db_res = [art]
                break
                
    if db_res:
        # Article exists, let's update it to ensure it matches details exactly!
        art = db_res[0]
        art.sector = item['sector']
        art.event_class = item['event_class']
        art.direction = item['direction']
        art.direction_reason = item['reason']
        art.is_relevant = item['is_relevant']
        if 'impact_score' in item:
            art.impact_score = item['impact_score']
        art.save()
        count_updated += 1
        continue
        
    # Article does not exist, let's find its full details!
    link = '#'
    description = ''
    summary = ''
    published_date = None
    
    # 1. Try to find in log
    match = log_by_title.get(norm_title)
    if not match:
        # fuzzy prefix match in log
        for k, v in log_by_title.items():
            if k.startswith(norm_title[:20]) or norm_title.startswith(k[:20]):
                match = v
                break
                
    if match:
        link = match.get('link') or '#'
        description = match.get('description') or match.get('scraped_content') or ''
        summary = match.get('analysis', {}).get('summary') or match.get('summary') or match.get('insights') or ''
        pub_date_str = match.get('published_date')
        if pub_date_str:
            try:
                published_date = datetime.strptime(pub_date_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
            except Exception:
                try:
                    from dateutil import parser as date_parser
                    published_date = date_parser.parse(pub_date_str)
                except Exception:
                    pass
    else:
        # 2. Try to find in splits
        match = split_by_title.get(norm_title)
        if match:
            link = match.get('link') or '#'
            description = match.get('description') or ''
            summary = match.get('summary') or match.get('insights') or ''
            pub_date_str = match.get('published_date')
            if pub_date_str:
                try:
                    from dateutil import parser as date_parser
                    published_date = date_parser.parse(pub_date_str)
                except Exception:
                    pass
                    
    # 3. If still not found anywhere, parse date from date string in item and use reason as summary
    if not published_date:
        date_str = item.get('date') # e.g. "15 Jun 2026"
        try:
            published_date = datetime.strptime(date_str, '%d %b %Y')
        except Exception:
            published_date = datetime.now()
            
    if not summary:
        summary = item.get('reason') or ''
        
    if not description:
        description = summary
        
    if published_date and not published_date.tzinfo:
        published_date = make_aware(published_date)
        
    try:
        NewsArticle.objects.create(
            title=title,
            link=link,
            source=item['source'],
            published_date=published_date,
            description=description,
            full_text=description,
            summary=summary,
            reason=summary,
            matched_keywords=[],
            is_relevant=item['is_relevant'],
            is_scraped=True,
            is_channel_mapped=True,
            event_class=item['event_class'],
            sector=item['sector'],
            sub_type=item['event_class'],
            channel=item['sector'],
            direction=item['direction'],
            direction_reason=item['reason'],
            impact_score=item.get('impact_score', 0),
            origin='Global'
        )
        count_added += 1
    except Exception as e:
        print(f"Error creating article {title[:40]}: {e}")
        count_errors += 1

print(f"Process complete. Added: {count_added}, Updated: {count_updated}, Errors: {count_errors}")
