import docx
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

docx_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\Docs_DB\docs_7_Days.docx"
doc = docx.Document(docx_path)

articles = []
current_article = None
state = None

for p in doc.paragraphs:
    text_content = p.text.strip()
    if not text_content:
        continue
        
    # Check for Heading 2 or matching title format
    if p.style.name.startswith('Heading 2') or re.match(r"^3\.\d+\s+", text_content):
        if current_article:
            articles.append(current_article)
        
        # Extract title
        match = re.match(r"^3\.\d+\s+(.*)", text_content)
        title = match.group(1) if match else text_content
        current_article = {
            'title': title,
            'source': 'Economic News',
            'published_date': '',
            'origin': 'Global',
            'sector': 'General / Macro',
            'event_class': 'Economic Impact',
            'direction': 'neutral',
            'summary': '',
            'direction_reason': '',
            'link': '#'
        }
        state = 'META'
        continue
        
    if not current_article:
        continue
        
    lines = [l.strip() for l in text_content.split('\n') if l.strip()]
    
    for text in lines:
        if state == 'META':
            if text.startswith('Source:'):
                m = re.match(r"Source:\s*(.*?)\s*\|\s*Published:\s*(.*?)\s*\|\s*Origin:\s*(.*)", text)
                if m:
                    current_article['source'] = m.group(1).strip()
                    current_article['published_date'] = m.group(2).strip()
                    current_article['origin'] = m.group(3).strip()
            elif text.startswith('Sector:'):
                m = re.match(r"Sector:\s*(.*?)\s*\|\s*Event Class:\s*(.*)", text)
                if m:
                    current_article['sector'] = m.group(1).strip()
                    current_article['event_class'] = m.group(2).strip()
            elif text.startswith('Direction:'):
                current_article['direction'] = text.replace('Direction:', '').strip().lower()
            elif text == 'Insight & Summary':
                state = 'INSIGHT'
            elif text == 'Sentiment Justification':
                state = 'REASON'
            elif text.startswith('Original Source Link:'):
                current_article['link'] = text.replace('Original Source Link:', '').strip()
                
        elif state == 'INSIGHT':
            if text == 'Sentiment Justification':
                state = 'REASON'
            elif text.startswith('Original Source Link:'):
                current_article['link'] = text.replace('Original Source Link:', '').strip()
                state = 'META'
            else:
                current_article['summary'] = (current_article['summary'] + "\n" + text).strip()
                
        elif state == 'REASON':
            if text.startswith('Original Source Link:'):
                current_article['link'] = text.replace('Original Source Link:', '').strip()
                state = 'META'
            else:
                current_article['direction_reason'] = (current_article['direction_reason'] + "\n" + text).strip()

if current_article:
    articles.append(current_article)

print(f"Total articles parsed: {len(articles)}")

# Now import them into Django database
count_added = 0
count_existing = 0

for art in articles:
    title = art['title']
    link = art['link']
    pub_date_str = art['published_date']
    
    # Parse datetime
    pub_date = None
    if pub_date_str:
        try:
            pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d %H:%M:%S')
        except Exception:
            try:
                from dateutil import parser as date_parser
                pub_date = date_parser.parse(pub_date_str)
            except Exception:
                pass
    if pub_date and not pub_date.tzinfo:
        pub_date = make_aware(pub_date)
        
    if not pub_date:
        pub_date = make_aware(datetime.now())
        
    # Check if duplicate title exists in DB
    if NewsArticle.objects.filter(title=title, published_date=pub_date).exists():
        count_existing += 1
        continue
        
    # Determine relevance (default True, unless explicitly False or set to 0 in curate script)
    # Let's keep it as relevant if it is relevant. 
    # Wait, we want to match the relevance from docs_7_Days.docx or curate_database_final.py!
    # Let's check: in docs_7_Days.docx, all 168 articles are logged. But wait, in the filtered report, only 52 are kept!
    # Let's see if we should just mark all of them as relevant first, and then run `curate_database_final.py` to curate it!
    # Yes! That is exactly what curate_database_final.py or curate_database_correct.py expects!
    # So we set is_relevant=True, and then we will run `curate_database_final.py` to apply the exact 52-article filter!
    
    try:
        NewsArticle.objects.create(
            title=title,
            link=link,
            source=art['source'],
            published_date=pub_date,
            description=art['summary'], # Use summary as description
            full_text=art['summary'],
            summary=art['summary'],
            reason=art['summary'],
            matched_keywords=[],
            is_relevant=True,
            is_scraped=True,
            is_channel_mapped=True,
            event_class=art['event_class'],
            sector=art['sector'],
            sub_type=art['event_class'], # fallback
            channel=art['sector'], # fallback
            direction=art['direction'],
            direction_reason=art['direction_reason'],
            impact_score=0, # default 0 or we can parse it from other details
            origin=art['origin']
        )
        count_added += 1
    except Exception as e:
        print(f"Error creating article {title[:40]}: {e}")

print(f"Import process complete. Added: {count_added}, Existing/Skipped: {count_existing}")
