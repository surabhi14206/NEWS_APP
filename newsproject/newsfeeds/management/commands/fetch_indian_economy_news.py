import json
import time
import ollama
import feedparser
import requests
from datetime import datetime, timedelta
# from bs4 import BeautifulSoup  # Web scraping HTML parsing disabled

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from newsfeeds.models import NewsArticle
from keywords2 import tema_keywords, sector_keywords   # Make sure this file is accessible
from .channel_maps import ChannelMapper, CHANNEL_MAP
from .ollama_ch_maps import OllamaChannelMapper

channel_mapper = ChannelMapper()
ollama_channel_mapper = OllamaChannelMapper()
# ====================== CONFIG ======================
from newsfeeds.spacy_utils import extract_locations_hybrid
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_AVAILABLE = True

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
}

RSS_FEEDS = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Bloomberg Business": "https://feeds.bloomberg.com/business/news.rss",
    "Reuters": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
    "Financial Times": "https://feeds.ft.com/ftcom/world",
    "Bloomberg Economics": "https://feeds.bloomberg.com/economics/news.rss",
    "CNBC": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "Bloomberg Markets": "https://feeds.bloomberg.com/markets/news.rss",
    "CNBC": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    "Bloomberg Wealth": "https://feeds.bloomberg.com/wealth/news.rss",
    "WION": "https://www.wionews.com/rss",
    "Asia Times": "https://asiatimes.com/feed",
    "The Diplomat": "https://thediplomat.com/feed",
    "Hindustan Times": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    "Times of India": "https://timesofindia.indiatimes.com/rssfeedsto/2965858.cms",
    "The Economic Times": "https://economictimes.indiatimes.com/rss/news",
    "Business Standard": "https://www.business-standard.com/rss/economy-policy-104.rss",
    "Mint": "https://www.livemint.com/rss/economy",
    "Moneycontrol": "https://www.moneycontrol.com/rss/economy.xml"
}


# ====================== HELPER FUNCTIONS ======================
def get_all_keywords():
    all_keywords = set()
    for l1 in tema_keywords.values():
        for l2_list in l1.values():
            for kw in l2_list:
                all_keywords.add(kw.lower())
    return all_keywords

ALL_KEYWORDS = get_all_keywords()


import re

def matches_specific_keywords(title: str, description: str) -> bool:
    text = (title + " " + description).lower()
    
    # Extract all alphanumeric words as a set to perform O(1) matching
    words = set(re.findall(r'[a-z0-9\-]+', text))
    
    # Specific geographical and economic terms indicating Indian relevance
    india_indicators = {
        "india", "indian", "rbi", "rupee", "rupees", "nifty", "sensex", "delhi", "mumbai", 
        "modi", "sitharaman", "sebi", "g-sec", "bps", "gst", "pli", "ibc", "fdi", "fii", "dii",
        "cad", "bop", "capex", "iip", "niti"
    }
    
    # Specific global macro indicators
    global_macro = {
        "inflation", "cpi", "wpi", "pmi", "recession", "crude", "oil", "commodity", "commodities",
        "tariff", "tariffs", "trade", "deficit", "surplus", "exports", "imports", "fed",
        "monetary", "fiscal", "budget", "gdp", "bonds", "yields"
    }
    
    # Match any whole word
    if words.intersection(india_indicators) or words.intersection(global_macro):
        return True
        
    return False


def get_keyword_mapping():
    mapping = {}
    for l1, l2_dict in tema_keywords.items():
        for l2, keywords_list in l2_dict.items():
            for kw in keywords_list:
                mapping[kw.lower()] = (l1, l2, kw)
    return mapping

KEYWORD_MAPPING = get_keyword_mapping()


def normalize_class_for_mapper(cls: str) -> str:
    cls_lower = cls.lower().replace('_', '').replace(' ', '').replace('&', 'and').strip()
    if "commodity" in cls_lower:
        return "commodity"
    if "climate" in cls_lower:
        return "climate_natural"
    if "geo" in cls_lower:
        return "geopolitical"
    if "trade" in cls_lower:
        return "trade_policy"
    if "domestic" in cls_lower:
        return "domestic_policy"
    if "financial" in cls_lower:
        return "financial_market"
    return cls_lower


def get_channels_from_mapper(event_class: str, subtype: str, title: str = "", description: str = "", model_name: str = OLLAMA_MODEL) -> list[str]:
    # 1. Normalize event_class to mapper keys
    ec_mapped = normalize_class_for_mapper(event_class)
    
    # 2. Extract clean subtype (before parenthesis and lowercase snake_case)
    clean_sub = subtype.split('(')[0].strip()
    
    # Normalize name: replace space/dash/slash/underscore with empty string to compare shapes
    def clean_str(s: str) -> str:
        return s.lower().replace('_', '').replace(' ', '').replace('-', '').replace('/', '').replace('&', 'and').strip()
    
    target_sub = clean_str(clean_sub)
    
    # Find all valid subtypes for this event_class in CHANNEL_MAP
    valid_subtypes = [k[1] for k in CHANNEL_MAP.keys() if k[0] == ec_mapped]
    
    # Match 1: Exact cleaned match
    matched_sub = None
    for vs in valid_subtypes:
        if clean_str(vs) == target_sub:
            matched_sub = vs
            break
    
    # Match 2: If no exact cleaned match, check if clean_sub matches or contains/is contained in valid subtypes
    if not matched_sub:
        for vs in valid_subtypes:
            vs_clean = clean_str(vs)
            if vs_clean in target_sub or target_sub in vs_clean:
                matched_sub = vs
                break
    
    # Match 3: Let's also do some semantic or manual mapping for known mismatches:
    if not matched_sub:
        # Domestic_Policy L2 mappings to CHANNEL_MAP keys
        if ec_mapped == "domestic_policy":
            if "monetary" in target_sub or "rbi" in target_sub:
                matched_sub = "rbi_rate_change"
            elif "fiscal" in target_sub or "budget" in target_sub:
                matched_sub = "fiscal_stimulus"
            elif "infra" in target_sub or "capex" in target_sub:
                matched_sub = "infrastructure_push"
            elif "regulatory" in target_sub or "reform" in target_sub:
                matched_sub = "regulatory_reform"
            elif "tax" in target_sub or "revenue" in target_sub:
                matched_sub = "gst_revision"
            elif "bank" in target_sub or "financial" in target_sub:
                matched_sub = "financial_sector_regulation"
            elif "pli" in target_sub or "industrial" in target_sub:
                matched_sub = "pli_industrial_policy"
            elif "agricultural" in target_sub or "farm" in target_sub:
                matched_sub = "agricultural_policy"
            elif "trade" in target_sub or "promotion" in target_sub:
                matched_sub = "trade_promotion_scheme"
        # Commodity_Shock L2 mappings
        elif ec_mapped == "commodity":
            if "oil" in target_sub or "energy" in target_sub:
                matched_sub = "crude_oil_price_change"
            elif "gas" in target_sub:
                matched_sub = "natural_gas_price_change"
            elif "food" in target_sub or "agri" in target_sub:
                matched_sub = "food_commodity_surge"
            elif "metal" in target_sub or "mining" in target_sub:
                matched_sub = "metal_price_change"
            elif "fertiliser" in target_sub or "fertilizer" in target_sub:
                matched_sub = "fertiliser_price_change"
            elif "critical" in target_sub or "mineral" in target_sub:
                matched_sub = "critical_mineral_restriction"
            elif "opec" in target_sub:
                matched_sub = "supply_cut_opec"
            elif "weather" in target_sub:
                matched_sub = "supply_disruption_weather"
            elif "china" in target_sub:
                matched_sub = "demand_shift_china"
            elif "reserve" in target_sub:
                matched_sub = "strategic_reserve_action"
            elif "supply" in target_sub or "chain" in target_sub or "geopolitics" in target_sub:
                matched_sub = "critical_mineral_restriction"
        # Financial_Market mappings
        elif ec_mapped == "financial_market":
            if "fed" in target_sub or "rate" in target_sub:
                matched_sub = "fed_rate_change"
            elif "dollar" in target_sub or "fx" in target_sub or "currency" in target_sub:
                matched_sub = "dollar_movement"
            elif "flow" in target_sub or "capital" in target_sub:
                matched_sub = "em_capital_flow"
            elif "rating" in target_sub:
                matched_sub = "sovereign_rating_change"
            elif "risk" in target_sub:
                matched_sub = "global_risk_off"
            elif "banking" in target_sub or "liquidity" in target_sub:
                matched_sub = "banking_sector_stress"
            elif "bond" in target_sub or "yield" in target_sub:
                matched_sub = "bond_yield_movement"
            elif "intervention" in target_sub:
                matched_sub = "currency_intervention"
            elif "equity" in target_sub or "market" in target_sub or "crash" in target_sub:
                matched_sub = "equity_market_crash"
        # Climate_Natural mappings
        elif ec_mapped == "climate_natural":
            if "monsoon" in target_sub or "deficit" in target_sub:
                matched_sub = "monsoon_deficit"
            elif "flood" in target_sub or "cyclone" in target_sub or "disaster" in target_sub:
                matched_sub = "flood_cyclone"
            elif "elnino" in target_sub or "lanina" in target_sub:
                matched_sub = "el_nino_la_nina"
            elif "food" in target_sub or "agri" in target_sub or "crisis" in target_sub:
                matched_sub = "global_food_crisis"
            elif "drought" in target_sub:
                matched_sub = "drought"
            elif "heat" in target_sub or "wave" in target_sub:
                matched_sub = "heat_wave"
            elif "earthquake" in target_sub:
                matched_sub = "earthquake"
            elif "crop" in target_sub or "damage" in target_sub:
                matched_sub = "crop_damage"
            elif "water" in target_sub:
                matched_sub = "water_scarcity"
            elif "air" in target_sub or "quality" in target_sub or "pollution" in target_sub:
                matched_sub = "air_quality_crisis"
    
    # 3. Call standard mapper first
    res = None
    if matched_sub:
        res = channel_mapper.map(ec_mapped, [matched_sub])
        
    # 4. If nothing comes, fall back to Ollama dynamic mapper
    if not res or not res.channels:
        subtypes_list = [matched_sub] if matched_sub else [clean_sub]
        res = ollama_channel_mapper.map_dynamic(
            event_class=ec_mapped,
            subtypes=subtypes_list,
            title=title,
            description=description,
            model_name=model_name
        )
        
    if res and res.channels:
        # Return a list of channel names
        return [ch["name"] for ch in res.channels]
    
    return []


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
        
    # Map matched sector to how the impact is channelized
    channel_mapping = {
        "Banking_and_Finance": "Interest Rates & Credit",
        "Stock_Market_and_Capital_Markets": "Capital Flows & Valuation",
        "Manufacturing_Sector": "Industrial Output & PLI",
        "IT_and_ITeS_Sector": "Services Exports & Hiring",
        "Energy_and_Power_Sector": "Import Bill & Energy Cost",
        "Automobile_and_Auto_Components": "Consumer Demand & EV Shift",
        "Agriculture_and_Allied_Sectors": "Rural Income & Food Inflation",
        "Real_Estate_and_Construction": "Infrastructure & Home Sales",
        "Pharmaceuticals_and_Healthcare": "CDMO & Pharma Exports",
        "Consumer_Goods_and_FMCG": "Consumer Demand & Inflation",
        "Metals_and_Mining": "Raw Material Costs & Output",
        "Logistics_and_Transportation": "Supply Chain & Freight Cost",
        "Telecom_and_Digital_Economy": "5G Rollout & Digital Adoption",
        "Insurance_Sector": "Retail Lending & Protection",
        "Aviation_and_Airlines": "Passenger Traffic & Fuel Cost",
        "Tourism_and_Hospitality": "Services Demand & Forex Inflow",
        "Education_Sector": "EdTech & Private Education",
        "Chemicals_and_Petrochemicals": "Specialty Chemical Exports",
        "Defense_and_Aerospace": "Atmanirbhar Defence & Exports",
        "Textiles_and_Apparel": "Textile Exports & Garment Jobs",
        "Retail_and_Ecommerce": "Retail Spending & E-commerce",
        "Startups_and_Venture_Capital": "Venture Capital & Unicorns",
        "General / Macro": "Macro Transmission & GDP"
    }
    fallback_channel = channel_mapping.get(best_sector, "Macroeconomic Transmission")
        
    if matched_kws:
        # Sort by matched keyword length descending to get the most specific keyword first
        matched_kws.sort(key=lambda x: x[3], reverse=True)
        best_l1, best_l2, best_original_kw, _ = matched_kws[0]
        
        # Get up to 2 matched keywords under this L2
        l2_matches = []
        for m in matched_kws:
            if m[1] == best_l2 and m[2] not in l2_matches:
                l2_matches.append(m[2])
        l2_matches = l2_matches[:2]
        l2_matches_str = ", ".join(l2_matches)
        
        mapped_chans = get_channels_from_mapper(best_l1, best_l2, title, description)
        channel = " & ".join(mapped_chans) if mapped_chans else fallback_channel
        
        return {
            "event_class": best_l1,
            "sector": best_sector,
            "sub_type": f"{best_l2} ({l2_matches_str})",
            "channel": channel,
            "all_matched": list(dict.fromkeys([m[2] for m in matched_kws]))  # keep unique, preserve order
        }
        
    return {
        "event_class": "Macro_Economy",
        "sector": best_sector,
        "sub_type": f"General_Terms ({best_kw})" if best_kw != "Economy" else "General_Terms (General)",
        "channel": fallback_channel,
        "all_matched": []
    }


L1_DESCRIPTIONS = {
    "Domestic_Policy": "Policies related to Indian government budgets, taxation, central bank (RBI) monetary policy (repo rates, CRR, MPC), banking reforms, and domestic regulations.",
    "Climate_and_Natural": "Monsoons, El Nino, drought, extreme weather, agricultural crop damage, food inflation, and natural disasters affecting the economy.",
    "Financial_Market": "Stock market index movements (Nifty, Sensex), bond yields, equity markets, rupee/dollar FX rates, and systemic banking risk.",
    "Commodity_Shock": "Global/domestic price spikes and supply chain shocks in crude oil, gas, metals, gold, coal, and global shipping/freight rates.",
    "Geo_Political": "Wars, military conflicts, geopolitical tensions, international sanctions, cyber attacks, and bilateral/multilateral summits (G7, BRICS).",
    "Trade_Policy": "Tariffs, trade agreements (FTAs), import/export bans, trade balance, current account deficits, and FDI/FII inflows/outflows.",
    "Global_Factors": "Global economic growth, global inflation, policies of foreign central banks (US Fed, ECB), and global recession risks.",
    "Inflation_and_Pricing": "General inflation indicators (CPI, WPI), retail/wholesale prices, price-drivers, and policy responses to control inflation.",
    "Consumer_Sentiment_and_Demand": "Consumer spending, retail sales, private consumption, discretionary spending, premiumisation, and consumer/business sentiment indices.",
    "Macro_Economy": "General macroeconomic indicators (GDP growth, IIP, PMI), economic outlooks, and general economic growth discussions."
}

def get_taxonomy_str() -> str:
    lines = []
    for l1, l2_dict in tema_keywords.items():
        desc = L1_DESCRIPTIONS.get(l1, "")
        lines.append(f"### EVENT CLASS (L1): {l1}")
        lines.append(f"Description: {desc}")
        for l2, kw_list in l2_dict.items():
            kw_str = ", ".join(kw_list[:20])
            lines.append(f"  - Sub-type (L2): {l2}")
            lines.append(f"    Allowed Channels (Keywords): {kw_str}")
        lines.append("")
    return "\n".join(lines)

TAXONOMY_STR = get_taxonomy_str()

import difflib

def normalize_l1(e_class: str) -> str:
    if not e_class:
        return "Macro_Economy"
    valid_l1s = list(tema_keywords.keys())
    
    # 1. Exact clean match
    e_class_cleaned = e_class.lower().replace('_', '').replace(' ', '').replace('&', 'and').strip()
    for l1 in valid_l1s:
        l1_cleaned = l1.lower().replace('_', '').replace(' ', '').replace('&', 'and').strip()
        if e_class_cleaned == l1_cleaned:
            return l1
            
    # 2. Fuzzy match using difflib
    matches = difflib.get_close_matches(e_class, valid_l1s, n=1, cutoff=0.2)
    if matches:
        return matches[0]
        
    # 3. Overlap-based match
    best_match = "Macro_Economy"
    best_overlap = 0
    e_class_words = set(re.findall(r'[a-z0-9]+', e_class.lower()))
    for l1 in valid_l1s:
        l1_words = set(re.findall(r'[a-z0-9]+', l1.lower()))
        overlap = len(e_class_words.intersection(l1_words))
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = l1
            
    return best_match

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
            
    # 2. Ollama semantic mapping (added logic)
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
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.0}
            )
            ollama_sec = response['message']['content'].strip().replace('"', '').replace("'", "").strip()
            # Double check if it is a valid sector
            if ollama_sec in valid_sectors:
                return ollama_sec
            else:
                # Try exact clean match on what Ollama returned, just in case
                ollama_sec_cleaned = ollama_sec.lower().replace('_', '').replace(' ', '').replace('&', 'and').replace('/', 'and').strip()
                for sec in valid_sectors:
                    sec_cleaned_target = sec.lower().replace('_', '').replace(' ', '').replace('&', 'and').replace('/', 'and').strip()
                    if ollama_sec_cleaned == sec_cleaned_target:
                        return sec
        except Exception:
            # Fall back quietly to existing fuzzy logic if Ollama fails
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


def normalize_l2(e_class: str, s_type: str) -> str:
    if not e_class or e_class not in tema_keywords:
        e_class = "Macro_Economy"
    valid_l2s = list(tema_keywords[e_class].keys())
    if not s_type:
        return valid_l2s[0] if valid_l2s else "General_Terms"
        
    # Clean L2 part (before parenthesis)
    parsed_l2 = s_type.split('(')[0].strip()
    parsed_l2_cleaned = parsed_l2.lower().replace('_', '').replace(' ', '').replace('&', 'and').strip()
    
    # 1. Exact clean match
    for l2 in valid_l2s:
        l2_cleaned = l2.lower().replace('_', '').replace(' ', '').replace('&', 'and').strip()
        if parsed_l2_cleaned == l2_cleaned:
            return l2
            
    # 2. Fuzzy match using difflib
    matches = difflib.get_close_matches(parsed_l2, valid_l2s, n=1, cutoff=0.2)
    if matches:
        return matches[0]
        
    # 3. Overlap check
    best_match = valid_l2s[0] if valid_l2s else "General_Terms"
    best_overlap = 0
    parsed_words = set(re.findall(r'[a-z0-9]+', parsed_l2.lower()))
    for l2 in valid_l2s:
        l2_words = set(re.findall(r'[a-z0-9]+', l2.lower()))
        overlap = len(parsed_words.intersection(l2_words))
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = l2
            
    return best_match

def classify_article_with_ollama(title: str, description: str, full_text: str = "") -> dict:
    if not OLLAMA_AVAILABLE:
        return classify_article(title, description, full_text)
        
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
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.0}
        )
        content = response['message']['content'].strip()
        
        import re
        json_match = re.search(r'\{.*?\}', content, re.DOTALL)
        if not json_match:
            return classify_article(title, description, full_text)
            
        data = json.loads(json_match.group())
        
        e_class_raw = data.get('event_class', '').strip()
        sector_raw = data.get('sector', '').strip()
        s_type_raw = data.get('sub_type', '').strip()
        chan = data.get('channel', '').strip()
        
        # 1. Intelligent Normalization & Validation of event_class
        e_class = normalize_l1(e_class_raw)
            
        # 2. Intelligent Normalization & Validation of sector
        sector = normalize_sector(sector_raw)
            
        # 3. Intelligent Normalization & Validation of sub_type
        # Extract L2 name and details
        norm_l2 = normalize_l2(e_class, s_type_raw)
        
        # Parse details (keywords inside parenthesis)
        rest_of_st = s_type_raw.split('(', 1)[1] if '(' in s_type_raw else ')'
        rest_of_st = rest_of_st.strip().rstrip(')').strip()
        
        if not rest_of_st or rest_of_st.lower() in ("general", "terms", "none", "n/a", "other"):
            # Let's extract 1-2 words from title/description/content that are in the L2 keywords
            text_lower = (title + " " + description + " " + full_text).lower()
            l2_keywords = tema_keywords.get(e_class, {}).get(norm_l2, [])
            matched_kws = [kw for kw in l2_keywords if kw.lower() in text_lower]
            if matched_kws:
                rest_of_st = ", ".join(matched_kws[:2])
            else:
                rest_of_st = "General"
                
        s_type = f"{norm_l2} ({rest_of_st})"
                
        # 4. Validate channel using ChannelMapper first, fallback to Ollama/defaults
        mapped_chans = get_channels_from_mapper(e_class, norm_l2, title, description, model_name=OLLAMA_MODEL)
        if mapped_chans:
            channel = " & ".join(mapped_chans)
        else:
            if not chan or "ministry" in chan.lower() or "department" in chan.lower():
                channel = f"{sector.replace('_', ' ')} Transmission"
            else:
                channel = chan
            
        return {
            "event_class": e_class,
            "sector": sector,
            "sub_type": s_type,
            "channel": channel
        }
        
    except Exception as e:
        print(f"Ollama classification failed: {e}")
        return classify_article(title, description, full_text)




# ====================== WEB SCRAPING CODE (DISABLED/COMMENTED OUT PER USER REQUEST) ======================
# All web scraping, HTML downloading, and browser emulation is completely commented out/disabled.
# We generate output strictly using the RSS feed titles and descriptions already parsed offline.

class BotBlockedException(Exception):
    pass

def detect_video(url: str, soup=None) -> tuple[bool, str]:
    return False, "Disabled"

def fetch_article_text(url: str) -> tuple[str, bool, str]:
    return "", False, "Web scraping disabled."

def is_semantic_duplicate_ollama(title: str, description: str, existing_articles: list, model_name: str) -> dict:
    if not OLLAMA_AVAILABLE:
        return {"repeated": False, "reason": "Ollama offline fallback: Assuming unique."}
    if not existing_articles:
        return {"repeated": False, "reason": "No existing articles to compare with."}
        
    existing_list_str = ""
    for idx, art in enumerate(existing_articles[-15:]):
        existing_list_str += f"{idx+1}. Title: {art['title']}\n   Description: {art['description']}\n\n"
        
    prompt = f"""
You are a financial news editor. Below is a list of already selected unique news articles:
{existing_list_str}

Analyze this new article:
Title: {title}
Description: {description}

Determine if this new article is a semantic duplicate (i.e., reports the exact same event, announcement, or news story that is already captured in the list above, even if worded slightly differently). We want unique news only.

Return ONLY a valid JSON object in this exact format:
{{
  "repeated": true or false,
  "reason": "Detailed explanation of why it is repeated or unique"
}}
"""
    try:
        response = ollama.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}]
        )
        content = response['message']['content']
        import re
        json_match = re.search(r'\{.*?\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"repeated": False, "reason": "JSON parse failed"}
    except Exception as e:
        print(f"Semantic duplicate check failed: {e}")
        return {"repeated": False, "reason": f"Error: {e}"}


def is_multimedia_content_ollama(title: str, description: str, url: str, model_name: str) -> dict:
    prompt = f"""
You are a news content format analyzer.
Your task is to identify if the given news article is strictly a multimedia-only file (like a standalone video clip, a YouTube link, an audio file/MP3, a podcast, a GIF, or a image gallery slideshow) rather than a standard written/text news article.

Article Details:
Title: {title}
Description: {description}
URL: {url}

CRITICAL RULES:
1. Standard written/text news articles (e.g., from BBC, Reuters, Bloomberg, Economic Times, etc.) MUST NOT be classified as multimedia, even if the topic is highly visual (like strikes, explosions, protests), and even if the webpage might contain an embedded image or video player. As long as the news is presented as a written article, it is TEXT news, not multimedia.
2. ONLY classify as multimedia (is_multimedia = true) if the URL, title, or description explicitly indicates that the content itself is a video-only post, a podcast episode, an MP3 audio track, a video report/clip, a YouTube/Vimeo link, or a photo gallery.
3. Do NOT guess or speculate about the likelihood of the article having a video. Be conservative. If in doubt, assume it is standard text news (is_multimedia = false).

Return ONLY a valid JSON object in this format:
{{
  "is_multimedia": true or false,
  "reason": "Clear explanation of why this is classified as multimedia (only if is_multimedia is true) or text news."
}}
"""
    try:
        response = ollama.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}]
        )
        content = response['message']['content']
        import re
        json_match = re.search(r'\{.*?\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"is_multimedia": False, "reason": "JSON parse failed"}
    except Exception as e:
        print(f"Multimedia format check failed: {e}")
        return {"is_multimedia": False, "reason": f"Error: {e}"}


def is_relevant_to_india_economy(headline: str, description: str = "", model_name: str = OLLAMA_MODEL) -> dict:
    if not OLLAMA_AVAILABLE:
        return {
            "relevant": True,
            "reason": "Offline fast fallback: passed Keyword Pre-Filter (Ollama is offline)",
            "matched_keywords": []
        }
    prompt = f"""You are an expert financial and macroeconomic analyst.
Your task is to filter news articles strictly for direct, real, and substantial impact on the Indian economy, financial markets, central banking (RBI), corporate business, or international trade.

Headline: {headline}
Description: {description}

CRITICAL DIRECTIVES:
1. EXCLUDE all news articles that do not directly pertain to finance, macroeconomics, central banking, corporate markets, fiscal policy, monetary policy, or international commerce.
2. ABSOLUTELY EXCLUDE general crime, local arrests, court proceedings for criminal cases, dowry deaths, accidents, celebrity news, sports, entertainment, local protests, family tragedies, or gossip.
3. Do NOT make highly hypothetical or indirect assumptions (e.g., claiming a local murder/arrest is relevant because it could 'affect foreign investor sentiment' or 'influence social stability perception'). The connection to finance or economics must be direct and substantive.

Mark as RELEVANT (relevant = true) ONLY if it meets at least one of these criteria:
- DIRECT ECONOMIC POLICY: Central bank (RBI) actions, repo rates, interest rates, government budgets, GST, taxation, fiscal reforms.
- MACROECONOMICS: Inflation indices (CPI, WPI), GDP growth, IIP, PMI, trade deficit, balance of payments, currency exchange rates (INR value).
- CORPORATE & FINANCIAL MARKETS: Stock markets (Nifty, Sensex), major corporate mergers, SEBI regulations, banking sector reforms, corporate credit.
- GLOBAL SHOCKS: Major global commodity spikes (crude oil, natural gas, gold) or trade wars/FTAs that directly affect India's import bills, trade balance, or domestic prices.

Return ONLY a valid JSON object in this exact format:
{{
  "relevant": true or false,
  "reason": "A highly concise 2 to 3 sentence explanation outlining the specific, direct economic or financial impact of this news on India or the Indian economy.",
  "matched_keywords": ["economic keyword1", "economic keyword2"]
}}
"""
    try:
        response = ollama.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}]
        )
        content = response['message']['content']

        import re
        json_match = re.search(r'\{.*?\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"relevant": False, "reason": "JSON parse failed", "matched_keywords": []}
            
    except Exception as e:
        return {
            "relevant": True, 
            "reason": f"Offline relevance fallback: passed Keyword Pre-Filter (Ollama connection error: {str(e)})", 
            "matched_keywords": []
        }


def clean_generated_text(text: str) -> str:
    if not text:
        return text
    
    import re
    # Remove leading conversational sentences ending with a colon
    text = re.sub(r"^(Here is|Here's|Here are|Based on|This article|In this|A short).*?:\s*", "", text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove leading conversational sentences ending with a newline
    text = re.sub(r"^(Here is|Here's|Here are).*?(summary|overview|options).*?\n+", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"^(Based on the).*?\n+", "", text, flags=re.IGNORECASE | re.DOTALL)
    
    # If the LLM still provided "Option 1... Option 2...", extract just Option 1
    match = re.search(r"Option 1.*?:\s*\"?(.*?)\"?(?=\s*Option 2|$)", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        text = match.group(1).strip()
        
    # Strip trailing questions
    text = re.sub(r"(Would you like|Do you want|Let me know if).*?\?$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    
    return text.strip()


def generate_summary(title: str, description: str, full_text: str = "") -> str:
    if not OLLAMA_AVAILABLE:
        summary_text = ""
        if description and len(description.strip()) > 20:
            summary_text = description.strip()
        else:
            summary_text = f"The article details the news event: '{title}'."
        return ' '.join(summary_text.split())

    if full_text and len(full_text) > 150:
        prompt = f"""
            Summarize the following news article in **4-5 comprehensive sentences**, providing a detailed and thorough overview of all key points.
            CRITICAL: Do NOT add any introductory phrases like "Here's a summary". 
            CRITICAL: Do NOT ask follow-up questions at the end like "Would you like me to...". 
            CRITICAL: Provide exactly ONE single summary. Do NOT provide multiple options (e.g., Option 1, Option 2).
            Just give the direct summary text and absolutely nothing else.

            Title: {title}
            Content: {full_text[:12000]}
            """
    else:
        prompt = f"""
            Create an informative, comprehensive summary of **3-4 descriptive sentences**, detailing the most important aspects.
            CRITICAL: Do NOT add any introductory phrases like "Here's a summary". 
            CRITICAL: Do NOT ask follow-up questions at the end like "Would you like me to...".
            CRITICAL: Provide exactly ONE single summary. Do NOT provide multiple options (e.g., Option 1, Option 2).
            Start directly with the summary and end immediately after.

            Title: {title}
            Description: {description}
            """

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': prompt}]
        )
        content = response['message']['content'].strip()
        
        return clean_generated_text(content)
    except Exception:
        return "Summary could not be generated."


def analyze_direction_from_india_view(title: str, description: str, summary: str = "") -> dict:
    if not OLLAMA_AVAILABLE:
        return {
            "direction": "neutral",
            "impact_score": 0,
            "reason": "Ollama offline fallback: Neutral economic impact default."
        }
    """
    Determines Positive / Negative / Neutral impact on India.
    """
    content = summary or description
    prompt = f"""
        You are a senior Indian economic analyst working for the Ministry of Finance / RBI.

        News Article:
        Title: {title}
        Content: {content[:8000]}

        Analyze the impact of this news **strictly from India's economic perspective** (rupee, inflation, exports, imports, FII/DII flows, RBI policy, growth, commodities, etc.).

        Return ONLY valid JSON in this exact format:
        {{
        "direction": "positive" or "negative" or "neutral",
        "impact_score": integer between -5 and +5,
        "reason": "One clear, concise sentence explaining the impact on India"
        }}

        Rules:
        - Use "positive" only if clearly beneficial for India.
        - Use "negative" only if clearly harmful for India.
        - Use "neutral" for no significant impact or mixed/unclear effects.
        - Do not use "mixed".
        """

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': prompt}]
        )
        content = response['message']['content']

        import re
        json_match = re.search(r'\{.*?\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            
            # Safety cleanup
            direction = result.get('direction', 'neutral').lower()
            if direction not in ['positive', 'negative', 'neutral']:
                direction = 'neutral'
                
            return {
                "direction": direction,
                "impact_score": int(result.get('impact_score', 0)),
                "reason": result.get('reason', 'No reason provided')
            }
            
    except Exception as e:
        print(f"Direction Analysis Error: {e}")
    
    return {
        "direction": "neutral",
        "impact_score": 0,
        "reason": "Analysis could not be completed"
    }


def identify_origin_with_ollama(title: str, description: str, summary: str = "", full_text: str = "") -> str:
    content = f"Title: {title}\nDescription: {description}\nSummary: {summary}"
    if full_text:
        content += f"\nFull Content: {full_text[:3000]}"
    
    prompt = f"""
You are a global news analyst. Determine which of the following countries are primary subjects or the main geographic focus of this news article: **India**, **US**, **Iran**, **China**.

Article Details:
{content}

Instructions:
1. Identify which of the key countries (India, US, Iran, China) are primary subjects or heavily involved in this news.
2. For each identified country, if a specific city, state, or region in that country is mentioned as the main location of the event, include it in parentheses (e.g., 'India (Mumbai)', 'US (Washington)', 'China (Beijing)'). If no specific city is mentioned, just output the country name (e.g., 'India').
3. If none of these four countries (India, US, Iran, China) is a primary subject, return 'Global' or 'Other'.
4. Format the final output as a clean, concise slash-separated list of identified origins (e.g., 'India (New Delhi)', 'US (Washington) / China (Beijing)', 'Iran', 'Global').
5. Return ONLY the final formatted string, with absolutely NO introduction, NO formatting markdown (like backticks or 'Output:'), and NO other explanation.

Examples:
- India (New Delhi)
- US (Washington) / China (Beijing)
- Iran
- Global
"""
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': prompt}]
        )
        origin_result = response['message']['content'].strip()
        origin_result = origin_result.replace("`", "").replace('"', "").replace("'", "").strip()
        origin_result = origin_result.split('\n')[0].strip()
        return origin_result or "Global"
    except Exception:
        return "Global"


# ====================== MAIN COMMAND ======================
class Command(BaseCommand):
    help = 'Fetch and analyze Indian Economy news from RSS feeds'

    def handle(self, *args, **options):
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            except Exception:
                pass
        self.stdout.write("Starting news analysis for Indian Economy...\n")
        
        # Check if local Ollama is running at startup to avoid slow socket connection timeouts
        global OLLAMA_AVAILABLE
        try:
            r = requests.get("http://localhost:11434/", timeout=0.3)
            OLLAMA_AVAILABLE = (r.status_code == 200)
        except Exception:
            OLLAMA_AVAILABLE = False
            
        if not OLLAMA_AVAILABLE:
            self.stdout.write("  [INFO] Local Ollama is offline. Resilient fast fallback mode enabled (bypassing connection timeouts).")
        
        now = datetime.now()
        
        # Smart Date Logic
        days_to_fetch = 3
        self.stdout.write(f"Fetching news from last {days_to_fetch} days\n")
        
        start_date = now - timedelta(days=days_to_fetch)
        self.stdout.write(f"Period: {start_date.strftime('%d-%m-%Y')} to {now.strftime('%d-%m-%Y')}\n")

        # Define configurations for both models
        configs = [
            {"model": "gemma3:4b", "log_file": "newsfeeds_scrape_log.json"},
            # {"model": "gemma4:e4b", "log_file": "gemma4_News.json"}
        ]

        # Step 1: RSS Feeds Fetch
        self.stdout.write("\n==================================================")
        self.stdout.write("STEP 1: RSS Feeds Fetch")
        self.stdout.write("==================================================")
        
        fetched_articles = []
        seen_identifiers = set()

        for source_name, rss_url in RSS_FEEDS.items():
            self.stdout.write(f"Fetching from: {source_name} ({rss_url})")
            try:
                feed = feedparser.parse(rss_url)
                for entry in feed.entries:
                    if not hasattr(entry, "published_parsed") or not entry.published_parsed:
                        continue
                    
                    published_date = datetime(*entry.published_parsed[:6])
                    if published_date < start_date or published_date > now:
                        continue
                    
                    title = entry.title.strip() if hasattr(entry, "title") else ""
                    link = entry.link.strip() if hasattr(entry, "link") else ""
                    description = getattr(entry, 'description', '') or getattr(entry, 'summary', '')
                    description = description.strip()
                    
                    if not title or not link:
                        continue
                        
                    # Basic exact duplicate check to avoid feed noise
                    identifier = (title.lower(), link.lower())
                    if identifier in seen_identifiers:
                        continue
                    seen_identifiers.add(identifier)
                    
                    fetched_articles.append({
                        "title": title,
                        "link": link,
                        "description": description,
                        "source": source_name,
                        "published_date": published_date.isoformat()
                    })
            except Exception as e:
                self.stdout.write(f"Error fetching from {source_name}: {e}")

        self.stdout.write(f"Total raw RSS feeds fetched: {len(fetched_articles)}")

        # Step 2: Show output of it (in console)
        self.stdout.write("\n==================================================")
        self.stdout.write("STEP 2: Output of Fetched RSS Feeds")
        self.stdout.write("==================================================")
        for idx, art in enumerate(fetched_articles):
            self.stdout.write(f"{idx+1}. [{art['source']}] {art['title']} ({art['published_date']})")
            self.stdout.write(f"   URL: {art['link']}")

        # Helper to compute Jaccard Similarity for headlines
        def get_jaccard_similarity(title1: str, title2: str) -> float:
            w1 = set(w for w in title1.lower().split() if w.isalnum())
            w2 = set(w for w in title2.lower().split() if w.isalnum())
            if not w1 or not w2:
                return 0.0
            return len(w1.intersection(w2)) / len(w1.union(w2))

        saved_count = 0

        # Now, run the processing pipeline for each model config
        for config in configs:
            global OLLAMA_MODEL
            OLLAMA_MODEL = config["model"]
            log_file = config["log_file"]

            self.stdout.write(f"\n\n##################################################")
            self.stdout.write(f"RUNNING PIPELINE WITH MODEL: {OLLAMA_MODEL}")
            self.stdout.write(f"TARGET LOG FILE: {log_file}")
            self.stdout.write(f"##################################################\n")

            # Reset tracking lists for this specific model run
            selected_articles = []
            rejected_articles = []
            all_articles_log = []
            
            # Step 3 & 4: Word-to-word deduplication
            word_selected_articles = []
            self.stdout.write(f"--- Running word-to-word duplicate cleaning ---")
            for art in fetched_articles:
                entry_log = {
                    "title": art["title"],
                    "link": art["link"],
                    "source": art["source"],
                    "published_date": art["published_date"],
                    "status": "pending",
                    "skip_reason": "",
                    "scraped_content": "",
                    "summary_generated": "",
                    "summary": "",
                    "insights_text": "",
                    "insights": {},
                    "steps": [],
                    "analysis": {}
                }
                
                duplicate_found = False
                duplicate_reason = ""
                
                for existing in word_selected_articles:
                    if art["title"].lower() == existing["title"].lower():
                        duplicate_found = True
                        duplicate_reason = f"Exact match with article: '{existing['title']}'"
                        break
                    
                    sim = get_jaccard_similarity(art["title"], existing["title"])
                    if sim >= 0.8:
                        duplicate_found = True
                        duplicate_reason = f"Highly similar headline (Jaccard sim: {sim:.2f}) to: '{existing['title']}'"
                        break
                        
                if duplicate_found:
                    entry_log["status"] = "skipped_duplicate_headline"
                    entry_log["skip_reason"] = duplicate_reason
                    entry_log["steps"].append({
                        "step": "Word-to-word Cleaning",
                        "status": "REJECTED",
                        "detail": duplicate_reason
                    })
                    rejected_articles.append(entry_log)
                    all_articles_log.append(entry_log)
                else:
                    entry_log["steps"].append({
                        "step": "Word-to-word Cleaning",
                        "status": "PASSED",
                        "detail": "No similar headline found in selected articles."
                    })
                    art_copy = dict(art)
                    word_selected_articles.append(art_copy)
                    art_copy["entry_log"] = entry_log

            self.stdout.write(f"Word-to-word cleaning complete. {len(word_selected_articles)} passed, {len(rejected_articles)} rejected.\n")

            # Step 2: Keyword Deduplication/Filtering (Keyword Pre-Filter)
            self.stdout.write(f"\n--- Filter if content matches keywords (Keyword Pre-Filter) ---")
            pre_filtered_articles = []
            for art in word_selected_articles:
                entry_log = art["entry_log"]
                if not matches_specific_keywords(art["title"], art["description"]):
                    # Irrelevant based on keyword list
                    entry_log["status"] = "skipped_not_relevant"
                    entry_log["skip_reason"] = "Keyword Pre-Filter: No specific economic, financial, or Indian keywords matched."
                    entry_log["steps"].append({
                        "step": "Relevance Check (Keyword Pre-Filter)",
                        "status": "REJECTED",
                        "detail": "Skipped. Title and description do not contain high-fidelity economic or geographical terms."
                    })
                    rejected_articles.append(entry_log)
                    all_articles_log.append(entry_log)
                else:
                    pre_filtered_articles.append(art)
            
            self.stdout.write(f"Keyword pre-filter complete. {len(pre_filtered_articles)} passed out of {len(word_selected_articles)}.\n")

            # Step 3: Semantic Deduplication via Ollama (On keyword-passed articles only)
            self.stdout.write(f"--- Running semantic duplicate cleaning on keyword-passed articles ---")
            semantic_unique_articles = []
            for art in pre_filtered_articles:
                entry_log = art["entry_log"]
                self.stdout.write(f"  Checking semantic duplicate of: \"{art['title']}\"...")
                try:
                    dup_result = is_semantic_duplicate_ollama(art["title"], art["description"], semantic_unique_articles, OLLAMA_MODEL)
                except Exception as e:
                    dup_result = {"repeated": False, "reason": f"Ollama error: {e}"}
                
                if dup_result.get("repeated", False):
                    self.stdout.write(f"  -> REJECTED as semantic duplicate: {dup_result.get('reason', '')}")
                    entry_log["status"] = "skipped_semantic_duplicate"
                    entry_log["skip_reason"] = f"Semantic duplicate check: {dup_result.get('reason', '')}"
                    entry_log["steps"].append({
                        "step": "Semantic Deduplication",
                        "status": "REJECTED",
                        "detail": dup_result.get("reason", "")
                    })
                    rejected_articles.append(entry_log)
                    all_articles_log.append(entry_log)
                else:
                    entry_log["steps"].append({
                        "step": "Semantic Deduplication",
                        "status": "PASSED",
                        "detail": f"Unique content confirmed by Ollama. Reason: {dup_result.get('reason', '')}"
                    })
                    semantic_unique_articles.append(art)
            
            self.stdout.write(f"Semantic cleaning complete. {len(semantic_unique_articles)} unique articles remaining.\n")

            # Step 4: High-Fidelity Relevance Check via local Ollama (On unique keyword-passed articles only)
            self.stdout.write(f"--- Filter if unique content is relevant (Relevance Check) ---")
            semantic_selected_articles = []
            
            if semantic_unique_articles:
                total_to_check = len(semantic_unique_articles)
                self.stdout.write(f"Running LLM checks for {total_to_check} unique articles sequentially...")
                
                for idx, art in enumerate(semantic_unique_articles, 1):
                    self.stdout.write(f"  [{idx}/{total_to_check}] Checking relevance of: \"{art['title']}\"...")
                    entry_log = art["entry_log"]
                    try:
                        relevance = is_relevant_to_india_economy(art["title"], art["description"], OLLAMA_MODEL)
                    except Exception as e:
                        relevance = {"relevant": False, "reason": f"LLM error: {e}", "matched_keywords": []}
                        
                    entry_log["analysis"]["relevance"] = relevance
                    entry_log["insights"]["relevance"] = relevance
                    entry_log["insights_text"] = relevance.get('reason', '')
                    
                    if not relevance.get("relevant", False):
                        entry_log["status"] = "skipped_not_relevant"
                        entry_log["skip_reason"] = f"LLM marked irrelevant: {relevance.get('reason', '')}"
                        entry_log["steps"].append({
                            "step": "Relevance Check",
                            "status": "REJECTED",
                            "detail": f"Reason: {relevance.get('reason', '')}"
                        })
                        rejected_articles.append(entry_log)
                        all_articles_log.append(entry_log)
                    else:
                        entry_log["steps"].append({
                            "step": "Relevance Check",
                            "status": "PASSED",
                            "detail": f"Reason: {relevance.get('reason', '')}"
                        })
                        semantic_selected_articles.append(art)

            self.stdout.write(f"Relevance filtering complete. {len(semantic_selected_articles)} passed.\n")

            # Step 4: Process All Selected News Items (Strictly based on raw RSS feed)
            self.stdout.write(f"\n==================================================")
            self.stdout.write(f"STEP 4: Process RSS Feed Content (No Scraping)")
            self.stdout.write(f"==================================================")
            
            import csv
            import os
            
            final_selected_articles = []
            saved_count = 0
            
            def save_live_outputs_stream():
                """Helper to write live files on every single loop iteration"""
                output_log_structure = {
                    "fetched_rss_feeds": [
                        {
                            "title": art["title"],
                            "link": art["link"],
                            "description": art.get("description", ""),
                            "source": art["source"],
                            "published_date": art["published_date"]
                        }
                        for art in fetched_articles
                    ],
                    "selected_articles": [
                        el for el in all_articles_log if el["status"] == "saved"
                    ],
                    "rejected_articles": [
                        el for el in all_articles_log if el["status"] != "saved"
                    ],
                    "all_articles_log": all_articles_log
                }
                
                # 1. Save JSON Log
                try:
                    with open(log_file, "w", encoding="utf-8") as f:
                        json.dump(output_log_structure, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    self.stdout.write(f"Warning: failed to save JSON log: {e}")
                
                # 2. Save CSV
                try:
                    os.makedirs("Outputs/OP_Scraper", exist_ok=True)
                    scraped_csv = "Outputs/OP_Scraper/articles_with_scraped_content.csv"
                    with open(scraped_csv, "w", newline="", encoding="utf-8") as csvfile:
                        fieldnames = ["#", "Title", "Source", "Published Date", "Scraped Content Length", "Summary", "Event Class", "Direction"]
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        for idx, art_log in enumerate(output_log_structure["selected_articles"], 1):
                            writer.writerow({
                                "#": idx,
                                "Title": art_log.get("title", "")[:100],
                                "Source": art_log.get("source", ""),
                                "Published Date": art_log.get("published_date", ""),
                                "Scraped Content Length": len(art_log.get("scraped_content", "")),
                                "Summary": art_log.get("summary_generated", "")[:200],
                                "Event Class": art_log.get("insights", {}).get("taxonomy", {}).get("event_class", ""),
                                "Direction": art_log.get("insights", {}).get("direction", {}).get("direction", "")
                            })
                except Exception as e:
                    pass
                
                # 3. Save Summary JSON
                try:
                    summary_json = "Outputs/OP_Scraper/scraped_content_summary.json"
                    summary_data = {
                        "total_selected": len(output_log_structure["selected_articles"]),
                        "total_rejected": len(output_log_structure["rejected_articles"]),
                        "articles": [
                            {
                                "title": art.get("title", ""),
                                "source": art.get("source", ""),
                                "link": art.get("link", ""),
                                "published_date": art.get("published_date", ""),
                                "scraped_content": art.get("scraped_content", ""),
                                "summary": art.get("summary_generated", ""),
                                "event_class": art.get("insights", {}).get("taxonomy", {}).get("event_class", ""),
                                "direction": art.get("insights", {}).get("direction", {}).get("direction", "")
                            }
                            for art in output_log_structure["selected_articles"]
                        ]
                    }
                    with open(summary_json, "w", encoding="utf-8") as f:
                        json.dump(summary_data, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    pass
                
                # 4. Save Detailed Markdown Files
                try:
                    articles_dir = "Outputs/OP_Scraper/articles_detailed"
                    os.makedirs(articles_dir, exist_ok=True)
                    
                    # Remove all old markdown files to keep directory fresh
                    for old_f in os.listdir(articles_dir):
                        if old_f.endswith(".md"):
                            try:
                                os.remove(os.path.join(articles_dir, old_f))
                            except Exception:
                                pass
                                
                    for idx, art_log in enumerate(output_log_structure["selected_articles"], 1):
                        safe_title = "".join(c for c in art_log.get("title", "untitled")[:80] if c.isalnum() or c in (' ', '-', '_')).strip()
                        md_file = os.path.join(articles_dir, f"{idx:03d}_{safe_title}.md")
                        
                        with open(md_file, "w", encoding="utf-8") as f:
                            f.write(f"# {art_log.get('title', 'N/A')}\n\n")
                            f.write(f"**Source:** {art_log.get('source', 'N/A')} | **Date:** {art_log.get('published_date', 'N/A')}\n\n")
                            f.write(f"**Link:** {art_log.get('link', 'N/A')}\n\n")
                            f.write(f"---\n\n")
                            
                            f.write(f"## 📰 RSS Feed Content (Title & Description)\n\n")
                            f.write(f"{art_log.get('scraped_content', '[No description available]')}\n\n")
                            
                            f.write(f"---\n\n")
                            f.write(f"## 📋 AI-Generated Summary\n\n")
                            f.write(f"{art_log.get('summary_generated', '[No summary generated]')}\n\n")
                            
                            f.write(f"---\n\n")
                            f.write(f"## 🏷️ Classification & Insights\n\n")
                            
                            insights = art_log.get("insights", {})
                            if insights:
                                f.write(f"- **Event Class:** {insights.get('taxonomy', {}).get('event_class', 'N/A')}\n")
                                f.write(f"- **Sector:** {insights.get('taxonomy', {}).get('sector', 'N/A')}\n")
                                f.write(f"- **Sub-Type:** {insights.get('taxonomy', {}).get('sub_type', 'N/A')}\n")
                                f.write(f"- **Channel:** {insights.get('taxonomy', {}).get('channel', 'N/A')}\n")
                                f.write(f"- **Sentiment:** {insights.get('direction', {}).get('direction', 'N/A')} (Score: {insights.get('direction', {}).get('impact_score', 0)})\n")
                                f.write(f"- **City/Country:** {insights.get('origin', 'N/A')}\n\n")
                            
                            f.write(f"---\n\n")
                            f.write(f"## ✅ Processing Steps\n\n")
                            for step in art_log.get("steps", []):
                                status_emoji = "✓" if step.get("status") == "PASSED" else "✗"
                                f.write(f"- {status_emoji} **{step.get('step', 'N/A')}** ({step.get('status', 'N/A')})\n")
                                f.write(f"  - {step.get('detail', '')}\n\n")
                except Exception as e:
                    pass

            total_relevant = len(semantic_selected_articles)
            
            if total_relevant == 0:
                self.stdout.write(f"\n==================================================")
                self.stdout.write(f"STEP 4: Process RSS Feed Content (No Scraping)")
                self.stdout.write(f"==================================================")
                self.stdout.write("No relevant unique articles found for processing.")
                self.stdout.write(f"==================================================")
                save_live_outputs_stream()
                continue
            
            self.stdout.write(f"Selected {total_relevant} articles for processing.")
            self.stdout.write(f"==================================================\n")
            
            for idx, art in enumerate(semantic_selected_articles, 1):
                self.stdout.write(f"\n>>> [{idx}/{total_relevant}] Processing: \"{art['title']}\" from [{art['source']}]")
                entry_log = art["entry_log"]
                
                # Fetch content directly from RSS description/title per user request
                full_text = art.get("description", "") or art.get("title", "")
                entry_log["scraped_content"] = full_text
                
                self.stdout.write(f"  Using RSS description ({len(full_text)} characters). Preview:")
                if full_text:
                    self.stdout.write(f"    \"{full_text[:300]}...\"")
                else:
                    self.stdout.write(f"    [Empty description. Using title as backup.]")
                    
                entry_log["steps"].append({
                    "step": "RSS Feed Reading",
                    "status": "PASSED" if full_text else "WARNING",
                    "detail": f"Loaded description from RSS ({len(full_text)} characters)." if full_text else "No content returned."
                })
                
                # D. Multimedia Check
                self.stdout.write(f"  Checking multimedia format...")
                media_result = is_multimedia_content_ollama(art["title"], art["description"], art["link"], OLLAMA_MODEL)
                if media_result.get("is_multimedia", False):
                    self.stdout.write(f"  -> REJECTED as multimedia format: {media_result.get('reason', '')}")
                    entry_log["status"] = "skipped_multimedia"
                    entry_log["skip_reason"] = f"Ollama identified as non-text format: {media_result.get('reason', '')}"
                    entry_log["steps"].append({
                        "step": "Multimedia Filter",
                        "status": "REJECTED",
                        "detail": media_result.get("reason", "")
                    })
                    rejected_articles.append(entry_log)
                    all_articles_log.append(entry_log)
                    save_live_outputs_stream()
                    continue
                    
                entry_log["steps"].append({
                    "step": "Multimedia Filter",
                    "status": "PASSED",
                    "detail": "Confirmed as written/text news article format."
                })
                
                # E. Summary Generation based strictly on title & description
                self.stdout.write(f"  Generating summary...")
                summary = generate_summary(art["title"], art["description"], entry_log["scraped_content"])
                entry_log["summary_generated"] = summary
                entry_log["summary"] = summary
                entry_log["analysis"]["summary"] = summary
                entry_log["steps"].append({
                    "step": "Generate Summary",
                    "status": "PASSED",
                    "detail": f"Summary: {summary[:100]}..."
                })
                
                # F. Metadata Analysis
                self.stdout.write(f"  Analyzing taxonomy class...")
                classification = classify_article_with_ollama(art["title"], art["description"], entry_log["scraped_content"])
                entry_log["analysis"]["taxonomy"] = classification
                entry_log["insights"]["taxonomy"] = classification
                entry_log["steps"].append({
                    "step": "Taxonomy Classification",
                    "status": "PASSED",
                    "detail": f"L1: {classification.get('event_class')}, L2: {classification.get('sub_type')}, Keyword: {classification.get('channel')}"
                })
                
                self.stdout.write(f"  Analyzing economic sentiment direction...")
                direction_result = analyze_direction_from_india_view(art["title"], art["description"], entry_log["summary_generated"])
                entry_log["analysis"]["direction"] = direction_result
                entry_log["insights"]["direction"] = direction_result
                entry_log["steps"].append({
                    "step": "Direction Analysis",
                    "status": "PASSED",
                    "detail": f"Direction: {direction_result.get('direction')}, Score: {direction_result.get('impact_score')}"
                })
                
                self.stdout.write(f"  Analyzing geographic origin...")
                try:
                    res_origin = extract_locations_hybrid(
                        title=art["title"],
                        description=art["description"],
                        full_text=entry_log["scraped_content"] or entry_log["summary_generated"],
                        model_name=OLLAMA_MODEL
                    )
                    origin = res_origin.get("origin", "Global")
                    
                    # Store detailed insights in entry_log
                    entry_log["analysis"]["origin_details"] = {
                        "cities": res_origin.get("cities", []),
                        "counties": res_origin.get("counties", []),
                        "locations": res_origin.get("locations", []),
                        "countries": res_origin.get("countries", []),
                        "confidence": res_origin.get("confidence", "high"),
                        "explanation": res_origin.get("explanation", "")
                    }
                except Exception as exc_origin:
                    self.stdout.write(f"  Origin identification failed: {exc_origin}, using default")
                    origin = "Global"

                entry_log["analysis"]["origin"] = origin
                entry_log["insights"]["origin"] = origin
                entry_log["steps"].append({
                    "step": "Geographic Origin",
                    "status": "PASSED",
                    "detail": f"Origin: {origin}"
                })
                
                # G. Save/Update in Django database
                self.stdout.write(f"  Saving to Django database...")
                try:
                    relevance_val = entry_log["analysis"]["relevance"]
                    pub_date = make_aware(datetime.fromisoformat(art["published_date"]))
                    
                    # Test to avoid duplicate news (check if title, link, and date all match an existing entry in DB)
                    if NewsArticle.objects.filter(
                        title=art["title"],
                        link=art["link"] or '#',
                        published_date=pub_date
                    ).exists():
                        self.stdout.write(f"  -> SKIPPED: Article is a duplicate (title, link, and date all match an existing entry in DB).")
                        entry_log["status"] = "skipped_duplicate_db"
                        entry_log["steps"].append({
                            "step": "Database Duplicate Check",
                            "status": "REJECTED",
                            "detail": "Article already exists in DB with identical title, link, and date."
                        })
                        all_articles_log.append(entry_log)
                        save_live_outputs_stream()
                        continue
                        
                    article_obj, created = NewsArticle.objects.update_or_create(
                        title=art["title"],
                        link=art["link"] or '#',
                        published_date=pub_date,
                        defaults={
                            'source': art["source"],
                            'description': art["description"],
                            'full_text': entry_log["scraped_content"],
                            'summary': entry_log["summary_generated"],
                            'reason': relevance_val.get('reason', ''),
                            'matched_keywords': relevance_val.get('matched_keywords', []),
                            'is_relevant': relevance_val.get('relevant', True),
                            
                            # Taxonomy
                            'event_class': classification['event_class'],
                            'sector': classification.get('sector', 'General / Macro'),
                            'sub_type': classification['sub_type'],
                            'channel': classification['channel'],
                            
                            # Sentiment
                            'direction': direction_result.get('direction', 'neutral'),
                            'impact_score': direction_result.get('impact_score', 0),
                            'direction_reason': direction_result.get('reason', ''),
                            
                            # Origin
                            'origin': origin
                        }
                    )
                    status_str = "Created" if created else "Updated"
                    entry_log["status"] = "saved"
                    entry_log["steps"].append({
                        "step": "Save to Database",
                        "status": "PASSED",
                        "detail": f"Successfully {status_str.lower()} article in database."
                    })
                    
                    saved_count += 1
                    self.stdout.write(f"  -> SUCCESS: Saved article to database.")
                except Exception as db_err:
                    self.stdout.write(f"  -> DB SAVE FAILED: {db_err}")
                    entry_log["status"] = "save_failed"
                    entry_log["skip_reason"] = f"DB Error: {str(db_err)}"
                    entry_log["steps"].append({
                        "step": "Save to Database",
                        "status": "FAILED",
                        "detail": f"Database save failed: {str(db_err)}"
                    })
                    
                # Append to selected and logs
                final_selected_articles.append(art)
                all_articles_log.append(entry_log)
                save_live_outputs_stream()
                
            self.stdout.write("\n==================================================")
            self.stdout.write("DUAL PIPELINE PROCESSING COMPLETE!")
            self.stdout.write(f"Saved/Updated news articles in DB: {saved_count}")
            self.stdout.write("==================================================")
            self.stdout.write("\n📁 Output Files Successfully Saved & Maintained:")
            self.stdout.write(f"  ├─ {log_file} (Full detailed log)")
            self.stdout.write("  ├─ Outputs/OP_Scraper/articles_with_scraped_content.csv (Summary table)")
            self.stdout.write("  ├─ Outputs/OP_Scraper/scraped_content_summary.json (Content JSON)")
            self.stdout.write("  └─ Outputs/OP_Scraper/articles_detailed/ (Individual markdown files)")
            self.stdout.write("==================================================")