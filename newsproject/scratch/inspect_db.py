import os
import sys
import django

# Setup Django settings context
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.models import NewsArticle

def main():
    print("=" * 80)
    print("INSPECTING NEWS ARTICLES DATABASE")
    print("=" * 80)
    
    # 1. Look for the specific article
    title_part = "Japan Adds to Steel"
    articles = NewsArticle.objects.filter(title__icontains=title_part)
    print(f"Found {articles.count()} articles matching '{title_part}':")
    for art in articles:
        print(f"ID: {art.id}")
        print(f"Title: {art.title}")
        print(f"Event Class: {art.event_class}")
        print(f"Sub-type: {art.sub_type}")
        print(f"Sector: {art.sector}")
        print(f"Channel: {art.channel}")
        print(f"Origin: {art.origin}")
        print(f"Is Relevant: {art.is_relevant}")
        print("-" * 50)
        
    # 2. Look for any articles with Ministry of Jal Shakti
    jal_articles = NewsArticle.objects.filter(channel__icontains="Jal Shakti")
    print(f"\nFound {jal_articles.count()} articles with 'Jal Shakti' channel:")
    for art in jal_articles:
        print(f"ID: {art.id} | Title: {art.title[:60]}... | Sector: {art.sector} | Channel: {art.channel}")
        
    print("=" * 80)

if __name__ == '__main__':
    main()
