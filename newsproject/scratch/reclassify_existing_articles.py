import os
import sys
import django

# Setup Django project path
sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.models import NewsArticle
from newsfeeds.management.commands.fetch_indian_economy_news import (
    classify_article_with_ollama,
    is_relevant_to_india_economy
)
from newsfeeds.spacy_utils import extract_locations_hybrid

def main():
    # Use standard UTF-8 output to prevent windows command prompt encoding failures
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        
    articles = NewsArticle.objects.filter(is_relevant=True)
    total = articles.count()
    print(f"Starting re-classification, location sanitization, and keyword reversion of {total} articles...\n")
    
    success_count = 0
    for idx, article in enumerate(articles, 1):
        # Strip or encode to prevent print errors
        safe_title = article.title.encode('ascii', 'ignore').decode('ascii')
        print(f"[{idx}/{total}] Processing: {safe_title[:65]}...")
        
        try:
            # 1. Fetch matched keywords from database or extract offline (zero LLM calls)
            matched_keywords = article.matched_keywords
            if not matched_keywords:
                from newsfeeds.management.commands.fetch_indian_economy_news import classify_article
                offline_class = classify_article(article.title, article.description, article.full_text)
                matched_keywords = offline_class.get("all_matched", [])
            
            # If no keywords are generated, fallback to the channel or clean title terms
            if not matched_keywords:
                matched_keywords = [article.channel] if article.channel else ["Indian Economy"]
                
            # 2. Re-run location sanitization (extract_locations_hybrid)
            res_origin = extract_locations_hybrid(
                title=article.title,
                description=article.description,
                full_text=article.full_text
            )
            origin = res_origin.get("origin", "Global")
                
            # 3. Run new high-fidelity semantic classification
            classification = classify_article_with_ollama(article.title, article.description, article.full_text)
            
            # 4. Save to database
            article.event_class = classification['event_class']
            article.sector = classification.get('sector', 'General / Macro')
            article.sub_type = classification['sub_type']
            article.channel = classification['channel']
            article.origin = origin
            article.matched_keywords = matched_keywords
            article.save()
            
            success_count += 1
            print(f"  -> Origin:      {article.origin}")
            print(f"  -> Event Class: {article.event_class}")
            print(f"  -> Sector:      {article.sector}")
            print(f"  -> Sub-type:    {article.sub_type}")
            print(f"  -> Channel:     {article.channel}")
            print(f"  -> Keywords:    {', '.join(article.matched_keywords)}")
            print("-" * 50)
            
        except Exception as e:
            print(f"  -> Error reclassifying article ID {article.id}: {e}")
            print("-" * 50)
            
    print(f"\nMigration Complete! Successfully reclassified and sanitized {success_count}/{total} articles in db.sqlite3.")

if __name__ == '__main__':
    main()
