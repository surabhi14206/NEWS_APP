import os
import sys
import django

# Setup Django project path
sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from newsfeeds.management.commands.fetch_indian_economy_news import (
    classify_article_with_ollama,
    normalize_l1,
    normalize_sector,
    normalize_l2
)
from newsfeeds.spacy_utils import extract_locations_hybrid

def test_normalization():
    print("=== Testing Fuzzy Normalization ===")
    
    # Test L1
    print("L1 Domestic Policy ->", normalize_l1("Domestic Policy"))
    print("L1 Climate and Natural ->", normalize_l1("Climate & Natural"))
    print("L1 invalid ->", normalize_l1("bizarre class name"))
    
    # Test Sector
    print("Sector Metals & Mining ->", normalize_sector("Metals & Mining"))
    print("Sector Banking and Finance ->", normalize_sector("Banking_and_Finance"))
    print("Sector invalid ->", normalize_sector("supermarket"))
    
    # Test L2
    print("L2 Monetary_RBI_Policy under Domestic_Policy ->", normalize_l2("Domestic_Policy", "Monetary RBI Policy"))
    print("L2 Fiscal_Policy under Domestic_Policy ->", normalize_l2("Domestic_Policy", "Fiscal Policy"))

def test_classification():
    print("\n=== Testing Ollama Semantic Classification & Location Extraction ===")
    
    title = "Japan initiates anti-dumping probe on steel imports from China and India"
    description = "Japan has officially started a major trade and anti-dumping investigation on hot-rolled steel plate imports coming from China and India, aiming to protect its domestic steel manufacturers."
    full_text = "The Ministry of Economy, Trade and Industry of Japan announced that they are looking into unfair trade practices. Steel giants like Nippon Steel had urged this probe due to falling prices and high supply from competitor countries."
    
    print("Article 1 Title:", title)
    
    # 1. Location Article 1
    loc_res = extract_locations_hybrid(title, description, full_text)
    print("Extracted Origin Article 1:", loc_res.get("origin"))
    
    # Test case 2: Coinbase Rupee Trading
    title2 = "Coinbase offers trading using Indian rupee - Reuters"
    desc2 = "Coinbase offers trading using Indian rupee - Reuters"
    print("\nArticle 2 Title:", title2)
    loc_res2 = extract_locations_hybrid(title2, desc2, "")
    print("Extracted Origin Article 2 (Rupee trading - should be just India):", loc_res2.get("origin"))
    
    # 2. Get prompt and run directly to inspect raw response
    from newsfeeds.management.commands.fetch_indian_economy_news import get_taxonomy_str, tema_keywords, sector_keywords, OLLAMA_MODEL
    import ollama
    import re
    
    taxonomy_str = get_taxonomy_str()
    prompt = f"""
You are a senior financial analyst and economic news classifier.
Your task is to analyze the news article below and classify it strictly from the perspective of India's economy, the Reserve Bank of India (RBI), Indian financial markets, corporate sectors, and macroeconomic transmission.

ORIGINAL L1 EVENT CLASSES:
{list(tema_keywords.keys())}

NEW 22 SPECIFIC SECTORS:
{list(sector_keywords.keys())}

EXAMPLE 1 (Monetary Policy Announcement):
Title: RBI raises repo rate by 25 bps to curb inflation
Description: The Reserve Bank of India's MPC has decided to hike the policy repo rate as retail inflation remains above the comfort zone.
Output:
{{
  "event_class": "Domestic_Policy",
  "sector": "Banking_and_Finance",
  "sub_type": "Monetary_RBI_Policy (Repo Rate, Rate Hike)",
  "channel": "Interest Rates & Credit"
}}

EXAMPLE 2 (Global Steel Tariffs):
Title: US imposes 25% tariff on steel imports to protect domestic industry
Description: The United States has announced new import duties on steel shipments from India and other countries, risking a retaliatory trade dispute.
Output:
{{
  "event_class": "Trade_Policy",
  "sector": "Metals_and_Mining",
  "sub_type": "Trade_Tensions_and_Tariffs (Import Duty, Trade Dispute)",
  "channel": "Export Competitiveness & Duties"
}}

ARTICLE TO CLASSIFY:
Title: {title}
Description: {description}
Content: {full_text[:3000]}

INSTRUCTIONS:
1. Identify the single best matching L1 EVENT CLASS from our taxonomy.
2. Identify the L2 sub-type key and select 1-2 most relevant keywords/phrases from that L2. Format the "sub_type" exactly as: "L2_Key (Keyword1, Keyword2)".
3. Select the primary matching SECTOR from the 22 SPECIFIC SECTORS list. If none fits well, output "General / Macro".
4. Generate a 2-4 word "channel" describing how this impact is transmitted to India.
5. Return ONLY a valid JSON object. Do not output any other text or explanation.
"""
    try:
        response = ollama.chat(
            model="gemma3:4b",
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.0}
        )
        raw_content = response['message']['content'].strip()
        print("\n--- Raw Ollama Output ---")
        print(raw_content)
        
        json_match = re.search(r'\{.*?\}', raw_content, re.DOTALL)
        if json_match:
            import json
            data = json.loads(json_match.group())
            print("\nParsed data fields:")
            print("  Raw event_class:", data.get("event_class"))
            print("  Raw sector:     ", data.get("sector"))
            print("  Raw sub_type:   ", data.get("sub_type"))
            print("  Raw channel:    ", data.get("channel"))
            
            # Print normalized results
            print("\nNormalized results:")
            print("  L1 normalizer ->", normalize_l1(data.get("event_class")))
            print("  Sector normalizer ->", normalize_sector(data.get("sector")))
            print("  L2 normalizer ->", normalize_l2(normalize_l1(data.get("event_class")), data.get("sub_type")))
    except Exception as e:
        print("Direct Ollama call failed:", e)

if __name__ == "__main__":
    test_normalization()
    test_classification()

