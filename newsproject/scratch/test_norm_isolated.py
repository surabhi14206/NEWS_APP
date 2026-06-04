import sys
import os
import difflib
import re
import json

# Add project path to sys.path
sys.path.append(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject")

from keywords2 import sector_keywords

OLLAMA_MODEL = "gemma3:4b"
OLLAMA_AVAILABLE = True

# Check if local Ollama is running
try:
    import requests
    r = requests.get("http://localhost:11434/", timeout=0.5)
    OLLAMA_AVAILABLE = (r.status_code == 200)
except Exception:
    OLLAMA_AVAILABLE = False

print(f"Ollama Available: {OLLAMA_AVAILABLE}")

def normalize_sector(sector: str) -> str:
    if not sector:
        return "General / Macro"
    valid_sectors = list(sector_keywords.keys()) + ["General / Macro"]
    
    # 1. Exact clean match
    sec_cleaned = sector.lower().replace('_', '').replace(' ', '').replace('&', 'and').replace('/', 'and').strip()
    for sec in valid_sectors:
        sec_cleaned_target = sec.lower().replace('_', '').replace(' ', '').replace('&', 'and').replace('/', 'and').strip()
        if sec_cleaned == sec_cleaned_target:
            return sec
            
    # 2. Ollama semantic mapping
    global OLLAMA_AVAILABLE
    if OLLAMA_AVAILABLE:
        try:
            prompt = f"""
You are a senior financial analyst and economic news classifier.
Your task is to map the raw, unnormalized sector string to the single best matching sector from our official 22 sectors list, or "General / Macro".

RAW SECTOR NAME TO MAP:
"{sector}"

OFFICIAL 22 SECTORS LIST:
{list(sector_keywords.keys())}

INSTRUCTIONS:
1. Select the single best matching sector from the official list that is semantically closest to the raw sector name.
2. If none of the 22 sectors are semantically related, return "General / Macro".
3. Return ONLY the exact sector name from the list (or "General / Macro"), with absolutely no other text, quote marks, markdown formatting, or explanation.
"""
            import ollama
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.0}
            )
            ollama_sec = response['message']['content'].strip().replace('"', '').replace("'", "").strip()
            if ollama_sec in valid_sectors:
                return ollama_sec
            else:
                ollama_sec_cleaned = ollama_sec.lower().replace('_', '').replace(' ', '').replace('&', 'and').replace('/', 'and').strip()
                for sec in valid_sectors:
                    sec_cleaned_target = sec.lower().replace('_', '').replace(' ', '').replace('&', 'and').replace('/', 'and').strip()
                    if ollama_sec_cleaned == sec_cleaned_target:
                        return sec
        except Exception as e:
            print(f"Ollama call failed: {e}")
            pass

    # 3. Fuzzy match using difflib
    matches = difflib.get_close_matches(sector, valid_sectors, n=1, cutoff=0.2)
    if matches:
        return matches[0]
        
    # 4. Word-level overlap check
    best_match = "General / Macro"
    best_overlap = 0
    sector_words = set(re.findall(r'[a-z0-9]+', sector.lower()))
    for sec in valid_sectors:
        sec_words = set(re.findall(r'[a-z0-9]+', sec.lower()))
        overlap = len(sector_words.intersection(sec_words))
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = sec
            
    return best_match

# Run tests
test_cases = [
    "Metals & Mining",           # Should match exact
    "Banking_and_Finance",       # Should match exact
    "supermarket",               # Should match "Retail_and_Ecommerce" via Ollama
    "car industry",              # Should match "Automobile_and_Auto_Components" via Ollama
    "pharma companies",          # Should match "Pharmaceuticals_and_Healthcare" via Ollama
    "completely unrelated topic" # Should match "General / Macro"
]

for tc in test_cases:
    print(f"Raw: {tc:30} -> Normalized: {normalize_sector(tc)}")
