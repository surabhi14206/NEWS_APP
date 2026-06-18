import json
import re

log_path = '../newsfeeds_scrape_log.json'
with open(log_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

log = data.get('all_articles_log', [])
selected = data.get('selected_articles', [])

targets = [
    "Razorpay Confidentially Files for $500 Million India IPO",
    "India facing uncertainty over forex, oil prices, rain shortfall, says finance minister",
    "US-Iran Peace Deal May Keep Rally in India Stocks, Rupee Going",
    "India, France to double trade in 5 years, eye greater cooperation in nuclear energy",
    "Modi, Macron launch Bharat Innovates; boost tech cooperation",
    "Modi, Trump set for first meeting since February amid trade, Iran war concerns",
    "US, India to tackle trade at G7 but deal not imminent, US officials say",
    "Exclusive: Tata's iPhone parts factory contaminated farmland water, India pollution body alleges",
    "Mint Explainer | What a strong El Nino could mean for India",
    "Rubio defends US blockade after EAM Jaishankar protests seafarers’ deaths",
    "“Be ready to respond”: India on highest alert, monitoring Hormuz after 3 seafarers killed in US strike"
]

print("SEARCHING LOG FILE FOR THE 11 MISSING ARTICLES:")
print("=" * 80)
for target in targets:
    print(f"Target: {target}")
    # Let's search for any overlap in title
    words = [w for w in re.split(r'\W+', target.lower()) if len(w) > 3]
    matches = []
    for art in log:
        title = art.get('title', '')
        # count matching words
        score = sum(1 for w in words if w in title.lower())
        if score >= len(words) * 0.4: # 40% word match
            matches.append((score, title, art.get('published_date'), art.get('status')))
            
    # Sort by score desc
    matches.sort(reverse=True, key=lambda x: x[0])
    for score, title, pub_date, status in matches[:3]:
        print(f"  Match (score={score}): {title} | Date: {pub_date} | Status: {status}")
    print("-" * 50)
