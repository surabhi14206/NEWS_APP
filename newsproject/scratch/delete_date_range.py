import os
import sys
import django
from datetime import datetime
from django.utils.timezone import make_aware

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.models import NewsArticle, DuplicateNewsArticle

# Define timezone-aware dates for June 13 to June 15, 2026
start_date = make_aware(datetime(2026, 6, 13, 0, 0, 0))
end_date = make_aware(datetime(2026, 6, 15, 23, 59, 59))

print(f"Filtering news articles between {start_date.isoformat()} and {end_date.isoformat()}...")

# Query before deleting
total_articles = NewsArticle.objects.filter(published_date__range=(start_date, end_date)).count()
total_duplicates = DuplicateNewsArticle.objects.filter(published_date__range=(start_date, end_date)).count()

print(f"Found {total_articles} articles and {total_duplicates} duplicate articles.")

# Deleting
deleted_articles, _ = NewsArticle.objects.filter(published_date__range=(start_date, end_date)).delete()
deleted_duplicates, _ = DuplicateNewsArticle.objects.filter(published_date__range=(start_date, end_date)).delete()

print(f"Successfully deleted {deleted_articles} news articles and {deleted_duplicates} duplicate news articles from database.")
