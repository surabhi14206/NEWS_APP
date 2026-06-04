import sys
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from newsfeeds.models import NewsArticle
from newsfeeds.spacy_utils import extract_locations_hybrid

class Command(BaseCommand):
    help = 'Identify City, County, Location, and Origin in the news articles using spaCy NER and Ollama.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Limit the number of articles to process.'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Re-process all articles, even if origin is already set.'
        )

    def handle(self, *args, **options):
        # Fix Windows console encoding for Unicode output
        if sys.platform == 'win32':
            os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

        limit = options.get('limit')
        process_all = options.get('all')

        if process_all:
            articles = NewsArticle.objects.filter(is_relevant=True)
        else:
            articles = NewsArticle.objects.filter(is_relevant=True)

        if limit is not None:
            articles = articles[:limit]

        total = articles.count()
        if total == 0:
            self.stdout.write("No articles found to analyze.\n")
            return

        model_name = getattr(settings, 'OLLAMA_MODEL', 'gemma3:4b')
        self.stdout.write(
            f"Running spaCy + Ollama ({model_name}) Location Identification on {total} articles...\n"
            f"{'=' * 80}\n"
        )

        for idx, article in enumerate(articles, 1):
            safe_title = article.title.encode('ascii', 'ignore').decode('ascii')
            self.stdout.write(f"\n[{idx}/{total}] ARTICLE: \"{safe_title[:80]}\"")
            self.stdout.write(f"Source: {article.source} | Date: {article.published_date}")
            
            try:
                res = extract_locations_hybrid(
                    title=article.title,
                    description=article.description,
                    full_text=article.full_text or article.summary,
                    model_name=model_name
                )
                
                origin_result = res.get("origin", "Global")
                
                # Save the refined origin back to database
                article.origin = origin_result
                article.save(update_fields=['origin'])

                self.stdout.write(f"  -> SUCCESSFUL EXTRACTION ({res.get('method')} mode):")
                self.stdout.write(f"     * Cities   : {res.get('cities')}")
                self.stdout.write(f"     * Counties : {res.get('counties')}")
                self.stdout.write(f"     * Locations: {res.get('locations')}")
                self.stdout.write(f"     * Countries: {res.get('countries')}")
                self.stdout.write(f"     * Origin   : {origin_result}")
                self.stdout.write(f"     * Confidence: {res.get('confidence')}")
                if res.get('explanation'):
                    self.stdout.write(f"     * Reason   : {res.get('explanation')}")

            except Exception as e:
                self.stdout.write(f"  -> ERROR extracting locations: {e}")

        self.stdout.write(f"\n{'=' * 80}\nDone processing {total} articles.\n")
