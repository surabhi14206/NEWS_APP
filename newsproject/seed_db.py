import json
import os
import django
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.models import NewsArticle, DuplicateNewsArticle

def run():
    print("Clearing database articles...")
    NewsArticle.objects.all().delete()
    DuplicateNewsArticle.objects.all().delete()
    
    # Path to training_data.json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, 'ML_Operation_Test_Train', 'training_data.json')
    
    print(f"Loading data from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Importing {len(data)} articles...")
    count = 0
    duplicate_count = 0
    
    for idx, item in enumerate(data):
        pub_date_str = item.get('published_date')
        if pub_date_str:
            pub_date = parse_datetime(pub_date_str)
            if pub_date is None:
                # Try simple ISO parsing
                try:
                    from dateutil import parser as date_parser
                    pub_date = date_parser.parse(pub_date_str)
                except Exception:
                    pass
            if pub_date and not pub_date.tzinfo:
                pub_date = make_aware(pub_date)
        
        if not pub_date:
            from datetime import datetime
            pub_date = make_aware(datetime.now())
            
        # Extract keywords list
        matched_kws = item.get('matched_keywords', [])
        if not matched_kws and item.get('sub_type'):
            matched_kws = [item.get('sub_type')]
            
        link = item.get('link') or '#'
        title = item.get('title')
        if not title:
            continue
            
        # Check if title, link, date already exists to handle unique constraint
        if NewsArticle.objects.filter(title=title, link=link, published_date=pub_date).exists():
            # Create in DuplicateNewsArticle instead
            DuplicateNewsArticle.objects.create(
                title=title,
                link=link,
                source=item.get('source') or 'Economic News',
                published_date=pub_date,
                description=item.get('description') or '',
                full_text=item.get('description') or '',
                summary=item.get('summary') or '',
                reason=item.get('insights') or '',
                matched_keywords=matched_kws,
                is_relevant=item.get('is_relevant', True),
                event_class=item.get('event_class') or 'Economic Impact',
                sector=item.get('sector') or 'General / Macro',
                sub_type=item.get('sub_type') or 'General News',
                channel=item.get('channel') or 'News & Media',
                direction=item.get('direction') or 'neutral',
                direction_reason=item.get('direction_reason') or '',
                impact_score=item.get('impact_score') or 0,
                origin=item.get('origin') or '',
                is_scraped=False,
                is_channel_mapped=True
            )
            duplicate_count += 1
        else:
            try:
                NewsArticle.objects.create(
                    title=title,
                    link=link,
                    source=item.get('source') or 'Economic News',
                    published_date=pub_date,
                    description=item.get('description') or '',
                    full_text=item.get('description') or '',
                    summary=item.get('summary') or '',
                    reason=item.get('insights') or '',
                    matched_keywords=matched_kws,
                    is_relevant=item.get('is_relevant', True),
                    event_class=item.get('event_class') or 'Economic Impact',
                    sector=item.get('sector') or 'General / Macro',
                    sub_type=item.get('sub_type') or 'General News',
                    channel=item.get('channel') or 'News & Media',
                    direction=item.get('direction') or 'neutral',
                    direction_reason=item.get('direction_reason') or '',
                    impact_score=item.get('impact_score') or 0,
                    origin=item.get('origin') or '',
                    is_scraped=False,
                    is_channel_mapped=True
                )
                count += 1
            except Exception as create_err:
                print(f"Error creating article {title[:30]}: {create_err}")
                
    print(f"Successfully imported {count} articles into NewsArticle.")
    print(f"Successfully imported {duplicate_count} articles into DuplicateNewsArticle.")

if __name__ == '__main__':
    run()
