import os
import sys
import django
import re

# Setup Django settings context
sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.models import NewsArticle, DuplicateNewsArticle

def derive_keywords(sector, event_class):
    # 1. If sector has parentheses, extract content inside parentheses (e.g. "Oil (Natural Gas)" -> "Natural Gas")
    m = re.search(r'\((.*?)\)', sector)
    if m:
        val = m.group(1).strip()
        # split by commas if it has multiple sub-types, e.g. "Exports, FTA"
        sub_vals = [v.strip() for v in val.split(',')]
        if sub_vals:
            return sub_vals
            
    # 2. Use clean sector name if it is not generic
    clean_sector = sector.replace('_', ' ').strip()
    if clean_sector and clean_sector.lower() not in ['', 'general', 'general / macro', 'macro']:
        return [clean_sector]
        
    # 3. Use event class as fallback
    clean_event = event_class.replace('_', ' ').strip()
    if clean_event and clean_event.lower() not in ['', 'general', 'general news', 'economic impact']:
        return [clean_event]
        
    return ['Economic News']

# Process NewsArticle
count_updated_na = 0
for art in NewsArticle.objects.all():
    if not art.matched_keywords or len(art.matched_keywords) == 0:
        kws = derive_keywords(art.sector, art.event_class)
        art.matched_keywords = kws
        art.save()
        count_updated_na += 1

# Process DuplicateNewsArticle
count_updated_dna = 0
for art in DuplicateNewsArticle.objects.all():
    if not art.matched_keywords or len(art.matched_keywords) == 0:
        kws = derive_keywords(art.sector, art.event_class)
        art.matched_keywords = kws
        art.save()
        count_updated_dna += 1

print(f"Update complete! Updated keywords for {count_updated_na} NewsArticles and {count_updated_dna} DuplicateNewsArticles.")
