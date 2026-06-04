import sys
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from newsfeeds.models import NewsArticle
from newsfeeds.spacy_utils import extract_locations_hybrid

OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'gemma3:4b')

class Command(BaseCommand):
    help = (
        'Analyze news articles using Ollama to identify their country '
        'of origin among India, US, Iran, China, or Global/Other, '
        'along with specific city details if mentioned.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Re-analyze ALL articles, even those that already have an origin value.'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of articles to process.'
        )

    def handle(self, *args, **options):
        # Fix Windows console encoding for Unicode output
        if sys.platform == 'win32':
            os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

        if options.get('all'):
            articles = NewsArticle.objects.filter(is_relevant=True)
        else:
            articles = NewsArticle.objects.filter(is_relevant=True, origin='')

        limit = options.get('limit')
        if limit is not None:
            articles = articles[:limit]

        total = articles.count()
        if total == 0:
            self.stdout.write("No articles found to analyze for origin. Use --all to force re-analysis.\n")
            return

        self.stdout.write(
            f"Analyzing country of origin for {total} articles "
            f"using Ollama ({OLLAMA_MODEL})...\n"
            f"{'-' * 70}\n"
        )

        success = 0
        failed = 0

        for idx, article in enumerate(articles, 1):
            safe_title = article.title.encode('ascii', 'ignore').decode('ascii')
            self.stdout.write(f"[{idx}/{total}] {safe_title[:70]}...")

            try:
                res = extract_locations_hybrid(
                    title=article.title,
                    description=article.description,
                    full_text=article.full_text or article.summary,
                    model_name=OLLAMA_MODEL
                )
                origin_result = res.get("origin", "Global")

                article.origin = origin_result
                article.save(update_fields=['origin'])

                self.stdout.write(f"  -> Origin: {origin_result}\n")
                self.stdout.write(f"     [spaCy Baseline] Cities: {res.get('spacy_found', {}).get('cities')}\n")
                self.stdout.write(f"     [Hybrid Extraction] Cities: {res.get('cities')} | Counties: {res.get('counties')} | Locations: {res.get('locations')}\n")
                self.stdout.write(f"     [Explanation] {res.get('explanation')}\n")
                success += 1

            except Exception as exc:
                self.stdout.write(f"  -> ERROR: {exc}\n")
                failed += 1

        self.stdout.write(
            f"\n{'-' * 70}\n"
            f"Done! Updated {success}/{total} articles  |  Failed: {failed}\n"
        )
