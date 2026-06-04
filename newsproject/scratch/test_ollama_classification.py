import os
import sys
import json
import re
import ollama

sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from keywords2 import tema_keywords

# Simplify taxonomy representation to minimize token size while keeping it complete
taxonomy_summary = {}
for l1, l2_dict in tema_keywords.items():
    taxonomy_summary[l1] = {}
    for l2, kw_list in l2_dict.items():
        taxonomy_summary[l1][l2] = kw_list

test_cases = [
    {
        "title": "Richemont Sales Up on Resilient Cartier Jewelry Demand",
        "description": "Richemont experienced a significant increase in sales for the fiscal year concluding in March, exceeding analyst expectations with an 11% rise on a constant currency basis. This growth was primarily driven by robust demand for Cartier's luxury jewelry, demonstrating resilience within the high-end market.",
    },
    {
        "title": "RBI MPC may pause repo rate hike as inflation drops",
        "description": "The Reserve Bank of India's Monetary Policy Committee is likely to maintain the repo rate as retail CPI inflation shows signs of easing.",
    },
    {
        "title": "Severe heat wave damages wheat crops in northern India",
        "description": "An intense heat wave and erratic southwest monsoon have raised concerns about agricultural GDP and food inflation.",
    }
]

prompt_template = """
You are a senior financial analyst and news classifier.
Your task is to classify the following news article into our predefined taxonomy.

Taxonomy:
{taxonomy_json}

Article to Classify:
Title: {title}
Description: {description}

Instructions:
1. Select the single best matching L1 category key (e.g., "Domestic_Policy") for "event_class".
2. Select the single best matching L2 subcategory key under that L1 (e.g., "Fiscal_Policy") for "sub_type".
3. Select the single best matching keyword string from the L2's list of keywords (e.g., "Fiscal Deficit") for "channel".

CRITICAL Rules:
- The selected "event_class" MUST be one of the top-level keys in the Taxonomy.
- The selected "sub_type" MUST be one of the keys under that specific "event_class".
- The selected "channel" MUST be exactly one of the strings inside that "sub_type"'s keyword list. Do not invent any new words or keys.
- Return ONLY a valid JSON object in this exact format:
{{
  "event_class": "...",
  "sub_type": "...",
  "channel": "..."
}}
"""

for idx, case in enumerate(test_cases, 1):
    prompt = prompt_template.format(
        taxonomy_json=json.dumps(taxonomy_summary, indent=2),
        title=case["title"],
        description=case["description"]
    )
    
    try:
        response = ollama.chat(
            model="gemma3:4b",
            messages=[{'role': 'user', 'content': prompt}]
        )
        content = response['message']['content']
        print(f"\n--- Case {idx} Raw Content ---")
        print(content)
        
        json_match = re.search(r'\{.*?\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            print(f"Parsed Result:")
            print(f"  Event Class: {result.get('event_class')}")
            print(f"  Sub Type: {result.get('sub_type')}")
            print(f"  Channel: {result.get('channel')}")
        else:
            print("Failed to find JSON block in response")
    except Exception as e:
        print(f"Error in Case {idx}: {e}")
