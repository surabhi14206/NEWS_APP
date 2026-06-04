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

# L1 Descriptions to help Gemma understand the categories semantically
L1_DESCRIPTIONS = {
    "Domestic_Policy": "Policies related to Indian government budgets, taxation, central bank (RBI) monetary policy (repo rates, CRR, MPC), banking reforms, and domestic regulations.",
    "Climate_and_Natural": "Monsoons, El Nino, drought, extreme weather, agricultural crop damage, food inflation, and natural disasters.",
    "Financial_Market": "Stock market index movements (Nifty, Sensex), bond yields, equity markets, rupee/dollar FX rates, and systemic banking risk.",
    "Commodity_Shock": "Global/domestic price spikes and supply chain shocks in crude oil, gas, metals, gold, coal, and global shipping/freight rates.",
    "Geo_Political": "Wars, military conflicts, geopolitical tensions, international sanctions, cyber attacks, and bilateral/multilateral summits (G7, BRICS).",
    "Trade_Policy": "Tariffs, trade agreements (FTAs), import/export bans, trade balance, current account deficits, and FDI/FII inflows/outflows.",
    "Global_Factors": "Global economic growth, global inflation, policies of foreign central banks (US Fed, ECB), and global recession risks.",
    "Inflation_and_Pricing": "General inflation indicators (CPI, WPI), retail/wholesale prices, price-drivers, and policy responses to control inflation.",
    "Consumer_and_Sentiment": "Consumer spending, retail sales, private consumption, discretionary spending, premiumisation, and consumer/business sentiment indices.",
    "General_Economic": "General macroeconomic indicators (GDP growth, IIP, PMI), economic outlooks, and general economic growth discussions."
}

# Represent taxonomy in a clean, high-density structured text format
taxonomy_text_lines = []
for l1, l2_dict in tema_keywords.items():
    desc = L1_DESCRIPTIONS.get(l1, "")
    taxonomy_text_lines.append(f"### EVENT CLASS (L1): {l1}")
    taxonomy_text_lines.append(f"Description: {desc}")
    for l2, kw_list in l2_dict.items():
        kw_str = ", ".join(kw_list[:20]) # Limit keywords to first 20 to avoid token bloat
        taxonomy_text_lines.append(f"  - Sub-type (L2): {l2}")
        taxonomy_text_lines.append(f"    Allowed Channels (Keywords): {kw_str}")
    taxonomy_text_lines.append("")

taxonomy_str = "\n".join(taxonomy_text_lines)

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
You are a senior financial analyst and economic news classifier.
Your task is to classify the news article below into our exact taxonomy.

TAXONOMY:
{taxonomy_str}

ARTICLE TO CLASSIFY:
Title: {title}
Description: {description}

INSTRUCTIONS:
1. Identify the single best matching EVENT CLASS (L1 category key, e.g., "Domestic_Policy") that represents the main topic of the news.
2. Select the single best matching SUB-TYPE (L2 key, e.g., "Monetary_RBI_Policy") from the L2 keys under the chosen L1.
3. Select the single best matching CHANNEL (Keyword string, e.g., "Repo Rate") from the list of allowed keywords under the chosen L2.

CRITICAL RULES:
- The selected "event_class" MUST be one of the "### EVENT CLASS (L1):" keys in the taxonomy.
- The selected "sub_type" MUST be one of the "Sub-type (L2):" keys listed under that event class.
- The selected "channel" MUST be EXACTLY one of the keyword strings inside the chosen sub-type's keyword list. Do not invent any new words, phrases, or keys.
- Return ONLY a valid JSON object in this exact format:
{{
  "event_class": "...",
  "sub_type": "...",
  "channel": "..."
}}
"""

for idx, case in enumerate(test_cases, 1):
    prompt = prompt_template.format(
        taxonomy_str=taxonomy_str,
        title=case["title"],
        description=case["description"]
    )
    
    try:
        response = ollama.chat(
            model="gemma3:4b",
            messages=[{'role': 'user', 'content': prompt}]
        )
        content = response['message']['content'].strip()
        print(f"\n--- Case {idx} Raw Content ---")
        # To avoid console encoding errors on Windows, print ASCII-only or clean output
        print(content.encode('ascii', 'ignore').decode('ascii'))
        
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
