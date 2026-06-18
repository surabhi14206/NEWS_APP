import json

filepath = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\newsfeeds_scrape_log.json"
with open(filepath, 'r', encoding='utf-8') as f:
    data = json.load(f)
selected = data.get('selected_articles', [])
rejected = data.get('rejected_articles', [])
all_log = data.get('all_articles_log', [])
print(f"Total: {len(all_log)}")
print(f"Selected: {len(selected)}")
print(f"Rejected: {len(rejected)}")
if all_log:
    print(f"Last processed title: {all_log[-1].get('title')}")
    print(f"Last processed status: {all_log[-1].get('status')}")
