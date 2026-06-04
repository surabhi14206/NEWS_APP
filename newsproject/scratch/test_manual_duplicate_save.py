import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newsproject.settings")
django.setup()

from newsfeeds.models import NewsArticle, DuplicateNewsArticle
from newsfeeds.management.commands.manual_analysis import process_manual_article

def run_test():
    test_title = "Test Unique Headline for Verification " + os.urandom(4).hex()
    test_art = {
        "title": test_title,
        "link": "https://example.com/verification-test-url",
        "description": "This is a verification test to check if duplicate manual articles are saved in a separate table.",
        "source": "Verification Test",
        "published_date": "2026-06-04T12:00:00"
    }

    print("Cleaning database...")
    NewsArticle.objects.filter(title=test_title).delete()
    DuplicateNewsArticle.objects.filter(title=test_title).delete()

    print("\n--- 1. First Insert (Should go to main NewsArticle table) ---")
    res1 = process_manual_article(test_art, save_to_db=True)
    print(f"Status: {res1['status']}")
    print(f"Reason: {res1.get('reason', 'N/A')}")
    print(f"Saved in NewsArticle: {NewsArticle.objects.filter(title=test_title).exists()}")

    print("\n--- 2. Second Insert (Duplicate, should go to DuplicateNewsArticle table) ---")
    res2 = process_manual_article(test_art, save_to_db=True)
    print(f"Status: {res2['status']}")
    print(f"Reason: {res2.get('reason', 'N/A')}")
    print(f"Saved in DuplicateNewsArticle: {DuplicateNewsArticle.objects.filter(title=test_title).exists()}")

    # Cleanup
    NewsArticle.objects.filter(title=test_title).delete()
    DuplicateNewsArticle.objects.filter(title=test_title).delete()

    if res1['status'] == 'success' and res2['status'] == 'saved_as_duplicate':
        print("\n>>> VERIFICATION SUCCESSFUL! <<<")
    else:
        print("\n>>> VERIFICATION FAILED! <<<")

if __name__ == "__main__":
    run_test()
