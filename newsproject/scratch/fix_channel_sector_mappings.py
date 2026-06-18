import os
import sys
import django

# Setup Django settings context
sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.models import NewsArticle, DuplicateNewsArticle
from newsfeeds.management.commands.fetch_indian_economy_news import classify_article

def process_articles(model_class, model_name):
    # Find articles where channel equals sector
    # We strip any sector keywords in parentheses to compare clean sector name, or we check if F('sector') == F('channel')
    # Let's inspect each article and see if channel is same as sector
    count_updated = 0
    qs = model_class.objects.all()
    print(f"Checking {qs.count()} {model_name}...")
    
    for art in qs:
        # Check if the clean sector name matches the clean channel name or if they are identical
        sec_clean = art.sector.split('(')[0].strip()
        chan_clean = art.channel.split('(')[0].strip()
        
        # If they are identical (like 'Banking_and_Finance' == 'Banking_and_Finance'), we reclassify
        if sec_clean == chan_clean or art.sector == art.channel:
            # Run offline rule-based classifier
            res = classify_article(art.title, art.description, art.full_text)
            
            # Update fields
            art.event_class = res['event_class']
            art.sector = res['sector']
            art.sub_type = res['sub_type']
            art.channel = res['channel']
            
            # Re-derive matched keywords if empty
            if not art.matched_keywords or len(art.matched_keywords) == 0:
                art.matched_keywords = res.get('all_matched', [])
                
            art.save()
            count_updated += 1
            print(f"  Updated: {art.title[:50]}...")
            print(f"    -> Sector: {art.sector} | Channel: {art.channel}")
            
    return count_updated

print("Starting fix for NewsArticle...")
updated_na = process_articles(NewsArticle, "NewsArticle")

print("\nStarting fix for DuplicateNewsArticle...")
updated_dna = process_articles(DuplicateNewsArticle, "DuplicateNewsArticle")

print(f"\nMigration complete! Updated {updated_na} NewsArticles and {updated_dna} DuplicateNewsArticles.")
