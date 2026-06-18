import os
import sys
import django

# Setup Django settings context
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.models import NewsArticle

count = NewsArticle.objects.filter(title__icontains='highest alert').update(is_relevant=True)
print(f"Updated {count} articles to is_relevant=True")
