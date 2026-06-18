import docx
import re
import os
import sys

docx_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\Docs_DB\docs_7_Days.docx"
doc = docx.Document(docx_path)

articles = []
current_article = None
state = None

for p in doc.paragraphs:
    text = p.text.strip()
    if not text:
        continue
        
    # Check for Heading 2 or matching title format
    if p.style.name.startswith('Heading 2') or re.match(r"^3\.\d+\s+", text):
        if current_article:
            articles.append(current_article)
        
        # Extract title
        match = re.match(r"^3\.\d+\s+(.*)", text)
        title = match.group(1) if match else text
        current_article = {
            'title': title,
            'source': '',
            'published_date': '',
            'origin': '',
            'sector': '',
            'event_class': '',
            'direction': '',
            'summary': '',
            'direction_reason': '',
            'link': ''
        }
        state = 'META'
        continue
        
    if not current_article:
        continue
        
    if state == 'META':
        if text.startswith('Source:'):
            m = re.match(r"Source:\s*(.*?)\s*\|\s*Published:\s*(.*?)\s*\|\s*Origin:\s*(.*)", text)
            if m:
                current_article['source'] = m.group(1).strip()
                current_article['published_date'] = m.group(2).strip()
                current_article['origin'] = m.group(3).strip()
        elif text.startswith('Sector:'):
            m = re.match(r"Sector:\s*(.*?)\s*\|\s*Event Class:\s*(.*)", text)
            if m:
                current_article['sector'] = m.group(1).strip()
                current_article['event_class'] = m.group(2).strip()
        elif text.startswith('Direction:'):
            current_article['direction'] = text.replace('Direction:', '').strip().lower()
        elif text == 'Insight & Summary':
            state = 'INSIGHT'
        elif text == 'Sentiment Justification':
            state = 'REASON'
        elif text.startswith('Original Source Link:'):
            current_article['link'] = text.replace('Original Source Link:', '').strip()
            
    elif state == 'INSIGHT':
        if text == 'Sentiment Justification':
            state = 'REASON'
        elif text.startswith('Original Source Link:'):
            current_article['link'] = text.replace('Original Source Link:', '').strip()
            state = 'META'
        else:
            current_article['summary'] = (current_article['summary'] + "\n" + text).strip()
            
    elif state == 'REASON':
        if text.startswith('Original Source Link:'):
            current_article['link'] = text.replace('Original Source Link:', '').strip()
            state = 'META'
        else:
            current_article['direction_reason'] = (current_article['direction_reason'] + "\n" + text).strip()

if current_article:
    articles.append(current_article)

print(f"Total articles parsed: {len(articles)}")
if articles:
    print("\nSAMPLE ARTICLE 1:")
    for k, v in articles[0].items():
        print(f"{k}: {repr(v)}")
        
    print("\nSAMPLE ARTICLE 60:")
    if len(articles) > 60:
        for k, v in articles[60].items():
            print(f"{k}: {repr(v)}")
