import sys
import os

# Setup Django settings context
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')

from keywords2 import tema_keywords, sector_keywords

# Mock KEYWORD_MAPPING
def get_keyword_mapping():
    mapping = {}
    for l1, l2_dict in tema_keywords.items():
        for l2, keywords_list in l2_dict.items():
            for kw in keywords_list:
                mapping[kw.lower()] = (l1, l2, kw)
    return mapping

KEYWORD_MAPPING = get_keyword_mapping()

def classify_article(title: str, description: str, full_text: str = "") -> dict:
    text = (title + " " + description + " " + full_text).lower()
    matched_kws = []
    
    for kw_lower, (l1, l2, kw_original) in KEYWORD_MAPPING.items():
        if kw_lower in text:
            matched_kws.append((l1, l2, kw_original, len(kw_lower)))
            
    # Rule-based sector matching
    sector_scores = {}
    matched_by_sector = {}
    for sector, keywords in sector_keywords.items():
        score = 0
        matches = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text:
                score += len(kw_lower)
                matches.append(kw)
        if score > 0:
            sector_scores[sector] = score
            matched_by_sector[sector] = matches
            
    best_sector = "General / Macro"
    if sector_scores:
        best_sector = max(sector_scores, key=sector_scores.get)
        
    best_kw = "Economy"
    if best_sector in matched_by_sector and matched_by_sector[best_sector]:
        best_kw = matched_by_sector[best_sector][0]
        
    if matched_kws:
        matched_kws.sort(key=lambda x: x[3], reverse=True)
        best_l1, best_l2, best_original_kw, _ = matched_kws[0]
        
        l2_matches = []
        for m in matched_kws:
            if m[1] == best_l2 and m[2] not in l2_matches:
                l2_matches.append(m[2])
        l2_matches = l2_matches[:2]
        l2_matches_str = ", ".join(l2_matches)
        
        return {
            "event_class": best_l1,
            "sector": best_sector,
            "sub_type": f"{best_l2} ({l2_matches_str})",
            "matched_by_sector": matched_by_sector,
            "matched_kws": matched_kws[:10]
        }
        
    return {
        "event_class": "General_Economic",
        "sector": best_sector,
        "sub_type": "General_Terms (General)",
        "matched_by_sector": matched_by_sector,
        "matched_kws": []
    }

def main():
    title = "Japan Adds to Steel Scrutiny With Probes on China, Taiwan, Korea"
    description = "Japan has launched an anti-dumping probe into imports of key steel products shipped from China, South Korea and Taiwan, adding to signs of trade stress in a sector suffering from global overcapacity."
    
    res = classify_article(title, description, description)
    import json
    print(json.dumps(res, indent=2))

if __name__ == '__main__':
    main()
