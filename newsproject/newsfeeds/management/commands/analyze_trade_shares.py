import io
import os
import sys
from django.core.management.base import BaseCommand
from newsfeeds.models import NewsArticle
from newsfeeds.management.commands.fetch_indian_economy_news import (
    analyze_trade_share_with_ollama
)


class Command(BaseCommand):
    help = (
        'Backfill trade_share analysis for existing articles '
        'using live World Bank macro data + local Ollama (gemma3:4b).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Re-analyze ALL relevant articles, even those that already have a trade_share value.'
        )

    def handle(self, *args, **options):
        # Fix Windows console encoding for Unicode output
        if sys.platform == 'win32':
            os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

        if options.get('all'):
            articles = NewsArticle.objects.filter(is_relevant=True)
        else:
            articles = NewsArticle.objects.filter(is_relevant=True, trade_share='')

        total = articles.count()
        if total == 0:
            self.stdout.write("All articles already have trade_share values. "
                              "Use --all to force re-analysis.\n")
            return

        self.stdout.write(
            f"Analyzing trade share for {total} articles "
            f"using World Bank API + Ollama (gemma3:4b)...\n"
            f"{'-' * 60}\n"
        )

        success = 0
        failed  = 0

        for idx, article in enumerate(articles, 1):
            safe_title = article.title.encode('ascii', 'ignore').decode('ascii')
            self.stdout.write(f"[{idx}/{total}] {safe_title[:70]}...")

            try:
                result = analyze_trade_share_with_ollama(
                    article.title,
                    article.description,
                    article.event_class,
                    article.channel,
                    article.summary,
                )
                article.trade_share = result
                article.save(update_fields=['trade_share'])
                self.stdout.write(f"  -> {result or '(empty)'}\n")
                success += 1

            except Exception as exc:
                self.stdout.write(f"  -> ERROR: {exc}\n")
                failed += 1

        self.stdout.write(
            f"\n{'-' * 60}\n"
            f"Done! Updated {success}/{total} articles  |  Failed: {failed}\n"
        )
