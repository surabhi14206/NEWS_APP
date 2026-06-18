import os
import sys
import django

# Add the directory containing manage.py to sys.path
sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.models import NewsArticle, DuplicateNewsArticle

# Query for DashboardView
qs_admin = NewsArticle.objects.filter(is_relevant=True)
qs_admin = qs_admin.exclude(summary__in=['', 'Summary could not be generated.', 'Summary could not be completed.', 'Summary could not be generated'])
qs_admin = qs_admin.exclude(reason__icontains='Ollama is offline')
admin_list = list(qs_admin.order_by('-published_date'))

# Query for UserDashboardView
qs_user = NewsArticle.objects.filter(is_relevant=True)
qs_user = qs_user.exclude(summary__in=['', 'Summary could not be generated.', 'Summary could not be completed.', 'Summary could not be generated'])
qs_user = qs_user.exclude(reason__icontains='Ollama is offline')
user_list = list(qs_user.order_by('-published_date'))

print(f"Admin queryset count: {len(admin_list)}")
print(f"User queryset count: {len(user_list)}")

# Are they identical?
diff = [a for a in admin_list if a not in user_list]
print(f"Admin articles not in User: {len(diff)}")

diff2 = [u for u in user_list if u not in admin_list]
print(f"User articles not in Admin: {len(diff2)}")

# Check duplicate counts
print(f"Duplicate articles count: {DuplicateNewsArticle.objects.count()}")
print(f"Manual articles count (is_relevant=False): {NewsArticle.objects.filter(is_relevant=False).count()}")
