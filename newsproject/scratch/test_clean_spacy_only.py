import re
import spacy

def clean_geotext(text: str) -> str:
    if not text:
        return ""
    # Remove standard URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove google news base64 patterns (e.g. CBMi...)
    text = re.sub(r'[A-Za-z0-9+/]{15,}=?\d*', '', text)
    # Remove any parameters like /articles/CBMi...
    text = re.sub(r'articles/[A-Za-z0-9+/=]+', '', text)
    return text.strip()

def is_valid_location(loc: str) -> bool:
    if not loc:
        return False
    # Reject strings containing URL/parameter symbols
    if any(c in loc for c in ('=', '?', '&', '/', '\\', '%', '_', '{', '}', '*', '[', ']')):
        return False
    # Reject typical "Other (CBMi...)" or base64 patterns
    loc_lower = loc.lower()
    if "other (" in loc_lower or "cbm" in loc_lower or "http" in loc_lower:
        return False
    # Reject long contiguous alphanumeric blocks
    words = loc.split()
    for w in words:
        if len(w) > 15 and not '-' in w:
            return False
    return True

def main():
    title = "Coinbase offers trading using Indian rupee - Reuters"
    description = '<a href="https://news.google.com/rss/articles/CBMilAFBVV95cUxQaXRnNXJsRkFlT3hEMnZIMWMzQm01MEtXX2lZZ3MtQjRISjV6eHdXWW9FaHhBMjV2M3JTby15R0pPVTA4Z283ekJRVkpUbVJaUzhTMnE3S3VqWDBPQ040emw4UkduRVVhdDRJQnp2Z1JxdjJxblg0NDR2ekNiMHp2OGFwcGFBSkVWT0NJdG9VQTJqYk02?oc=5" target="_blank">Coinbase offers trading using Indian rupee</a>&nbsp;&nbsp;<font color="#6f6f6f">Reuters</font>'
    
    cleaned_desc = clean_geotext(description)
    cleaned_title = clean_geotext(title)
    
    article_text = f"Title: {cleaned_title}\nDescription: {cleaned_desc}\n"
    
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(article_text)
    
    spacy_cities = []
    spacy_countries = []
    
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC"):
            text = ent.text.strip().replace("\n", " ")
            if not is_valid_location(text) or len(text) < 2 or re.match(r'^\d+$', text):
                continue
            spacy_cities.append(text)
            
    with open("scratch/test_spacy_only_result.txt", "w", encoding="utf-8") as f:
        f.write(f"Article Text for spaCy:\n{article_text}\n\n")
        f.write(f"spaCy Entities:\n")
        for ent in doc.ents:
            f.write(f"- {ent.text} ({ent.label_})\n")
        f.write(f"\nFiltered spacy_cities:\n{spacy_cities}\n")

if __name__ == '__main__':
    main()
