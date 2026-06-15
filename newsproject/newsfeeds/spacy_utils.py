import spacy
import ollama
import json
import re
from django.conf import settings
from typing import Dict, List

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    import subprocess
    import sys
    print("spaCy model 'en_core_web_sm' not found. Installing...")
    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

# Geopolitical data helper (geonamescache integration)
COMMON_COUNTRIES = set()
CITY_COUNTRY_MAP = {}
COMMON_STATES = {
    "uttar pradesh", "maharashtra", "bihar", "west bengal", "madhya pradesh", "tamil nadu",
    "rajasthan", "karnataka", "gujarat", "andhra pradesh", "odisha", "telangana", "kerala",
    "jharkhand", "assam", "punjab", "haryana", "chhattisgarh", "jammu", "kashmir", "uttarakhand",
    "himachal pradesh", "tripura", "meghalaya", "manipur", "nagaland", "goa", "arunachal pradesh",
    "mizoram", "sikkim", "delhi", "california", "texas", "florida", "new york state", "ontario",
    "bavaria", "quebec"
}

try:
    import geonamescache
    gc = geonamescache.GeonamesCache()
    geonames_countries = gc.get_countries()
    geonames_cities = gc.get_cities()
    
    # 1. Load countries
    for c_code, c_info in geonames_countries.items():
        c_name = c_info['name']
        COMMON_COUNTRIES.add(c_name.lower())
        if 'iso' in c_info and c_info['iso']:
            COMMON_COUNTRIES.add(c_info['iso'].lower())
        if 'iso3' in c_info and c_info['iso3']:
            COMMON_COUNTRIES.add(c_info['iso3'].lower())
            
    # Add common variants
    COMMON_COUNTRIES.update({
        "us", "usa", "united states", "united states of america",
        "uk", "united kingdom", "great britain", "uae", "united arab emirates"
    })
    
    # 2. Load cities (filtered by population >= 100,000 for accuracy)
    # Store population alongside mappings to resolve naming conflicts (prefer larger population)
    city_temp_resolution = {} # city_name_lower -> (country_name, population)
    
    for city_id, city_info in geonames_cities.items():
        pop = city_info.get('population', 0)
        if pop >= 100000:
            city_name_lower = city_info['name'].lower()
            c_code = city_info['countrycode']
            c_info = geonames_countries.get(c_code)
            if c_info:
                country_name = c_info['name']
                # If name conflict, select the city with the higher population
                if city_name_lower in city_temp_resolution:
                    existing_country, existing_pop = city_temp_resolution[city_name_lower]
                    if pop > existing_pop:
                        city_temp_resolution[city_name_lower] = (country_name, pop)
                else:
                    city_temp_resolution[city_name_lower] = (country_name, pop)
                    
    # Populate final map
    for city_name_lower, (country_name, _) in city_temp_resolution.items():
        CITY_COUNTRY_MAP[city_name_lower] = country_name
        
    # Ensure important overrides are present
    CITY_COUNTRY_MAP.update({
        "new delhi": "India",
        "bengaluru": "India",
        "bangalore": "India"
    })
    
except Exception as e:
    # Fallback to static mappings if geonamescache fails or is uninstalled
    COMMON_COUNTRIES = {
        "india", "united states", "us", "usa", "china", "iran", "united kingdom", "uk", "great britain",
        "germany", "france", "japan", "russia", "canada", "australia", "israel", "lebanon", "ukraine",
        "pakistan", "bangladesh", "sri lanka", "nepal", "bhutan", "maldives", "singapore", "malaysia",
        "indonesia", "thailand", "vietnam", "philippines", "south korea", "north korea", "saudi arabia",
        "uae", "united arab emirates", "qatar", "egypt", "south africa", "brazil", "mexico", "argentina",
        "italy", "spain", "netherlands", "switzerland", "sweden", "norway", "finland", "denmark",
        "turkey", "iraq", "syria", "afghanistan", "taiwan", "hong kong", "new zealand"
    }
    CITY_COUNTRY_MAP = {
        "mumbai": "India", "delhi": "India", "new delhi": "India", "bangalore": "India", "bengaluru": "India",
        "kolkata": "India", "chennai": "India", "hyderabad": "India", "pune": "India", "ahmedabad": "India",
        "bhopal": "India", "jabalpur": "India", "lucknow": "India", "gandhinagar": "India",
        "washington": "US", "new york": "US", "los angeles": "US", "chicago": "US", "san francisco": "US",
        "houston": "US", "miami": "US", "boston": "US", "seattle": "US", "beijing": "China", "shanghai": "China",
        "shenzhen": "China", "guangzhou": "China", "wuhan": "China", "tehran": "Iran", "isfahan": "Iran",
        "shiraz": "Iran", "tabriz": "Iran", "london": "UK", "paris": "France", "berlin": "Germany",
        "tokyo": "Japan", "moscow": "Russia", "toronto": "Canada", "sydney": "Australia", "tel aviv": "Israel",
        "beirut": "Lebanon", "kyiv": "Ukraine"
    }

def clean_geotext(text: str) -> str:
    if not text:
        return ""
    # Remove standard URLs
    text = re.sub(r'https?://\S+', '', text)
    # Strip HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    # Remove google news base64 patterns (e.g. CBMi...), including URL-safe base64 characters _ and -
    text = re.sub(r'[A-Za-z0-9+/_-]{12,}=?\d*', '', text)
    # Remove any parameters like /articles/CBMi...
    text = re.sub(r'articles/[A-Za-z0-9+/=_-]+', '', text)
    # Remove HTML entities like &nbsp;
    text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
    # Remove multiple whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_valid_location(loc: str) -> bool:
    if not loc:
        return False
    # Reject strings containing URL/parameter/code symbols
    if any(c in loc for c in ('=', '?', '&', '/', '\\', '%', '_', '{', '}', '*', '[', ']', '<', '>', ';')):
        return False
    # Reject typical "Other (CBMi...)" or base64 patterns
    loc_lower = loc.lower()
    if "other (" in loc_lower or "cbm" in loc_lower or "http" in loc_lower or "html" in loc_lower or "target=" in loc_lower:
        return False
    # Reject long contiguous alphanumeric blocks
    words = loc.split()
    for w in words:
        if len(w) > 15 and not '-' in w:
            return False
        # Reject random-looking alphanumeric mix (e.g. hash or base64 fragment)
        if len(w) > 8 and any(c.isdigit() for c in w) and any(c.isalpha() for c in w):
            return False
    return True

def extract_locations_hybrid(title: str, description: str = "", full_text: str = "", model_name: str = None) -> Dict:
    """
    Extracts City, County, Location, and Origin from a news article using spaCy NER
    and a robust rule-based geopolitical mapping (100% offline, zero Ollama calls).
    """
    # Clean inputs to prevent parser leakage of URL base64 parameters
    title = clean_geotext(title)
    description = clean_geotext(description)
    full_text = clean_geotext(full_text)

    # Construct complete text for parsing
    article_text = f"Title: {title}\n"
    if description:
        article_text += f"Description: {description}\n"
    if full_text:
        article_text += f"Full Text: {full_text[:4000]}\n"  # Limit context for efficiency

    # Step 1: spaCy NER extraction
    doc = nlp(article_text)
    spacy_cities = []
    spacy_counties = []
    spacy_locations = []
    spacy_countries = []

    # Geopolitical mappings helper
    country_matches = set()
    city_matches = []
    county_matches = []
    state_matches = []

    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC"):
            text = ent.text.strip().replace("\n", " ")
            # Ignore base64 parameter noise and tiny noisy terms
            if not is_valid_location(text) or len(text) < 2 or re.match(r'^\d+$', text):
                continue
            
            text_lower = text.lower()
            
            # Map alternate country names
            if text_lower in ("us", "usa", "united states", "united states of america"):
                country_matches.add("US")
                spacy_countries.append("US")
            elif text_lower in ("uk", "united kingdom", "great britain"):
                country_matches.add("UK")
                spacy_countries.append("UK")
            elif text_lower == "india":
                country_matches.add("India")
                spacy_countries.append("India")
            elif text_lower == "china":
                country_matches.add("China")
                spacy_countries.append("China")
            elif text_lower == "iran":
                country_matches.add("Iran")
                spacy_countries.append("Iran")
            elif text_lower in COMMON_COUNTRIES:
                # Capitalize nicely
                cname = text.title()
                country_matches.add(cname)
                spacy_countries.append(cname)
            elif "county" in text_lower or "district" in text_lower or "parish" in text_lower:
                spacy_counties.append(text)
                county_matches.append(text)
            elif text_lower in COMMON_STATES or ent.label_ == "LOC":
                spacy_locations.append(text)
                state_matches.append(text)
            else:
                spacy_cities.append(text)
                city_matches.append(text)
                # If the city is in our map, add its country too
                if text_lower in CITY_COUNTRY_MAP:
                    country_matches.add(CITY_COUNTRY_MAP[text_lower])

    # Clean duplicates while preserving order
    spacy_cities = list(dict.fromkeys(spacy_cities))
    spacy_counties = list(dict.fromkeys(spacy_counties))
    spacy_locations = list(dict.fromkeys(spacy_locations))
    spacy_countries = list(dict.fromkeys(spacy_countries))
    
    unique_countries = list(dict.fromkeys(country_matches))
    unique_cities = list(dict.fromkeys(city_matches))

    # Deduce primary geographic origin
    origin_parts = []
    
    # Priority country list for classification context
    priority_countries = ["India", "US", "Iran", "China"]
    
    # Identify if any country is explicitly mentioned (or implied by city) in the title
    title_countries = set()
    title_lower = title.lower()
    for country in COMMON_COUNTRIES:
        if re.search(r'\b' + re.escape(country) + r'\b', title_lower):
            if country in ("us", "usa", "united states"):
                title_countries.add("US")
            elif country in ("uk", "united kingdom"):
                title_countries.add("UK")
            else:
                title_countries.add(country.title())
    for country in ["india", "china", "iran"]:
        if re.search(r'\b' + re.escape(country) + r'\b', title_lower):
            title_countries.add(country.title())
    for city, country in CITY_COUNTRY_MAP.items():
        if re.search(r'\b' + re.escape(city) + r'\b', title_lower):
            title_countries.add(country)
            
    # If title countries are matched in the text, prioritize them
    title_matched = [c for c in unique_countries if c in title_countries]
    if title_matched:
        matched_priorities = title_matched
    else:
        matched_priorities = [c for c in priority_countries if c in unique_countries]

    if matched_priorities:
        # Use target priority countries
        for country in matched_priorities:
            # Find if there are any cities associated with this country
            matching_cities = [c for c in unique_cities if CITY_COUNTRY_MAP.get(c.lower()) == country]
            if matching_cities:
                origin_parts.append(f"{country} ({matching_cities[0]})")
            else:
                origin_parts.append(country)
    elif unique_countries:
        # Fallback to other matched countries
        for country in unique_countries[:2]:
            matching_cities = [c for c in unique_cities if CITY_COUNTRY_MAP.get(c.lower()) == country]
            if matching_cities:
                origin_parts.append(f"{country} ({matching_cities[0]})")
            else:
                origin_parts.append(country)
    elif unique_cities:
        # Fallback to matched cities
        for city in unique_cities[:2]:
            country = CITY_COUNTRY_MAP.get(city.lower(), "Other")
            origin_parts.append(f"{country} ({city})")
    
    origin_str = " / ".join(origin_parts) if origin_parts else "Global"

    # Check if spaCy succeeded in finding specific target countries/cities
    # If not, try Ollama as a high-fidelity fallback
    if not origin_parts or origin_str == "Global":
        # Fast port-check to verify if Ollama is online before making calls
        ollama_active = False
        import requests
        try:
            r = requests.get("http://localhost:11434/", timeout=0.2)
            if r.status_code == 200:
                ollama_active = True
        except Exception:
            ollama_active = False
            
        if ollama_active:
            if not model_name:
                model_name = getattr(settings, 'OLLAMA_MODEL', 'gemma3:4b')
                
            prompt = f"""You are an expert global news location analyst.
spaCy baseline NER failed to extract specific cities or target countries from this article.
Please read the article below and identify if the news event primarily focuses on or involves: **India**, **US**, **Iran**, or **China**.

Article Details:
{article_text}

Instructions:
1. Identify which of these four countries (India, US, Iran, China) is a primary subject.
2. If a specific city, state, or region in that country is explicitly mentioned by name in the text, extract it in parentheses (e.g., 'India (Mumbai)', 'US (Washington)'). If no specific city is written by name in the text, just output the country (e.g. 'India').
3. If none of these target countries is a primary subject, identify the general country and city explicitly mentioned in the text (e.g., 'UK (London)', 'Japan (Tokyo)').
4. If no specific country or city is written explicitly in the text, return 'Global'.

CRITICAL ANTI-HALLUCINATION DIRECTIVE:
- Do NOT guess, assume, or intelligently deduce any city, state, or region. You must ONLY output a city/region name if that specific name is explicitly written in the provided text.
- If the text only indicates a country (e.g., "rupee" indicates India, but no city is mentioned), you must output ONLY the country name (e.g., "India"), and NEVER add a parenthesized city (e.g., do NOT output "India (Mumbai)" or "India (Delhi)" unless "Mumbai" or "Delhi" is literally present in the text).

5. Return ONLY a valid JSON object in this exact format with NO markdown code blocks:
{{
  "cities": ["City Name"],
  "countries": ["Country Name"],
  "origin": "Country (City)"
}}
"""
            try:
                response = ollama.chat(
                    model=model_name,
                    messages=[{'role': 'user', 'content': prompt}],
                    options={'temperature': 0.0}
                )
                content = response['message']['content'].strip()
                json_match = re.search(r'\{.*?\}', content, re.DOTALL)
                if json_match:
                    ollama_result = json.loads(json_match.group())
                    
                    ollama_cities = ollama_result.get("cities", [])
                    ollama_countries = ollama_result.get("countries", [])
                    ollama_origin = ollama_result.get("origin", "Global")
                    
                    if ollama_origin and ollama_origin != "Global" and is_valid_location(ollama_origin):
                        return {
                            "cities": list(dict.fromkeys(spacy_cities + ollama_cities)),
                            "counties": spacy_counties,
                            "locations": spacy_locations,
                            "countries": list(dict.fromkeys(unique_countries + ollama_countries)),
                            "origin": ollama_origin,
                            "confidence": "medium (Ollama fallback)",
                            "spacy_found": {
                                "cities": spacy_cities,
                                "counties": spacy_counties,
                                "locations": spacy_locations,
                                "countries": spacy_countries
                            },
                            "explanation": "spaCy NER found no priority locations. Successfully resolved via local Ollama fallback.",
                            "method": "spacy_plus_ollama_fallback"
                        }
            except Exception as e:
                # Fallback failed, we stick with the spaCy default
                pass

    return {
        "cities": spacy_cities,
        "counties": spacy_counties,
        "locations": spacy_locations,
        "countries": unique_countries,
        "origin": origin_str,
        "confidence": "high (spaCy offline)",
        "spacy_found": {
            "cities": spacy_cities,
            "counties": spacy_counties,
            "locations": spacy_locations,
            "countries": spacy_countries
        },
        "explanation": "Extracted strictly using high-performance offline spaCy NER and rule-based geopolitical mapping.",
        "method": "spacy_offline"
    }
