import json

with open('../newsfeeds_scrape_log.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

log = data.get('all_articles_log', [])

terms = ['forex', 'shortfall', 'finance', 'minister', 'uncertainty', 'sitharaman']
for term in terms:
    matches = [a['title'] for a in log if term in a['title'].lower()]
    print(f"Term '{term}': {len(matches)} matches")
    for m in matches[:5]:
        print(f"  - {m}")
