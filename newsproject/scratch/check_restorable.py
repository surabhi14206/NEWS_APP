import json
import re

# Load all_128_details.json
with open('scratch/all_128_details.json', 'r', encoding='utf-8') as f:
    details = json.load(f)

# Load log
with open('../newsfeeds_scrape_log.json', 'r', encoding='utf-8') as f:
    log_data = json.load(f)
log_articles = log_data.get('all_articles_log', [])

# Load split datasets as fallback
splits = []
for fpath in ['../ML_Operation_Test_Train/no_use_data.json', '../ML_Operation_Test_Train/low_impact_events.json', '../ML_Operation_Test_Train/test_split.json']:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            splits.extend(json.load(f))
    except Exception:
        pass

def normalize(s):
    return re.sub(r'\W+', '', s.lower())

log_by_title = {normalize(a['title']): a for a in log_articles}
split_by_title = {normalize(a['title']): a for a in splits}

found_in_log = 0
found_in_splits = 0
not_found = []

for item in details:
    title = item['title']
    norm_title = normalize(title)
    
    # 1. Try exact/normalized match in log
    match = log_by_title.get(norm_title)
    if match:
        found_in_log += 1
        continue
        
    # 2. Try in splits
    match = split_by_title.get(norm_title)
    if match:
        found_in_splits += 1
        continue
        
    # 3. Try fuzzy prefix match
    fuzzy_match = None
    for k, v in log_by_title.items():
        if k.startswith(norm_title[:20]) or norm_title.startswith(k[:20]):
            fuzzy_match = v
            break
    if fuzzy_match:
        found_in_log += 1
        continue
        
    not_found.append(title)

print(f"Total target articles in details: {len(details)}")
print(f"Found in log: {found_in_log}")
print(f"Found in splits: {found_in_splits}")
print(f"Not found anywhere: {len(not_found)}")
if not_found:
    print("\nNOT FOUND TITLES:")
    for t in not_found:
        print(f"  - {t}")
