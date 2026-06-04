"""One-time script to replace analyze_trade_share_with_ollama with two-stage version."""
import pathlib

file_path = pathlib.Path(r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\newsfeeds\management\commands\fetch_indian_economy_news.py")

content = file_path.read_text(encoding='utf-8')

# The old single-stage function to find
OLD_FUNC_START = "def analyze_trade_share_with_ollama(title: str, description: str,"
OLD_FUNC_END   = "        return ''\n\n\n# ====================== MAIN COMMAND"

NEW_FUNC = '''def analyze_trade_share_with_ollama(title: str, description: str,
                                     event_class: str, channel: str,
                                     summary: str = '') -> str:
    """
    Two-stage trade share analysis:

    Stage 1 - Article extraction (Ollama only, no API needed):
        Ask gemma3:4b to look for specific trade share / import-export figures
        directly in the article content.
        If found  -> return the extracted phrase AS-IS (no prefix).
                     Frontend shows it WITHOUT the disclaimer info icon.

    Stage 2 - World Bank API estimate (fallback):
        If the article contains no trade-specific data, fetch live India macro
        indicators from the World Bank REST API (cached 24h, ~1 KB).
        Use those as context for an Ollama-generated estimate.
        Returns the phrase prefixed with "EST:" so the frontend knows to
        show the AI-Estimated disclaimer icon.
    """
    article_content = summary if (summary and len(summary) > 80) else description
    readable_class  = event_class.replace('L1_', '').replace('_', ' ')

    # -- STAGE 1: Try to extract real trade figures from article text ----------
    extraction_prompt = (
        "You are a trade data extraction specialist.\\n\\n"
        "ARTICLE:\\n"
        f"Headline : {title}\\n"
        f"Category : {readable_class} / {channel}\\n"
        f"Content  : {article_content[:3000]}\\n\\n"
        "TASK:\\n"
        "Does this article contain any SPECIFIC trade share, trade value, import/export\\n"
        "percentage, or trade volume data relevant to India or global trade?\\n\\n"
        "Examples of SPECIFIC data (good to extract):\\n"
        '- "India imports 85% of its crude oil needs"\\n'
        '- "exports worth $12 billion in Q1"\\n'
        '- "crude oil accounts for 35% of India\'s import bill"\\n'
        '- "trade deficit widened to $20.4B in April"\\n'
        '- "gold imports fell 18% to $3.2B month-on-month"\\n\\n'
        "If YES: Extract it as a single concise phrase (under 20 words). Be exact.\\n"
        "If NO specific trade data exists in the article: reply with exactly NO_TRADE_DATA\\n\\n"
        "Return ONLY the extracted phrase OR exactly: NO_TRADE_DATA"
    )

    try:
        resp1     = ollama.chat(model=OLLAMA_MODEL,
                                messages=[{'role': 'user', 'content': extraction_prompt}])
        extracted = resp1['message']['content'].strip().strip('"\\' ').strip()
        extracted = extracted.split('\\n')[0].strip()   # first line only

        # Valid extraction: not the sentinel and has meaningful length
        if extracted and extracted.upper() != 'NO_TRADE_DATA' and len(extracted) > 8:
            return extracted[:250]                       # no prefix = real data from article

    except Exception as exc:
        print(f"  [Trade Share S1] extraction failed: {exc}")

    # -- STAGE 2: No article trade data -> World Bank API + Ollama estimate ----
    ctx = fetch_remote_trade_context(event_class)

    estimation_prompt = (
        "You are an Indian trade economics analyst at a top-tier research firm.\\n\\n"
        f"INDIA MACRO TRADE DATA (Source: {ctx['source']}, {ctx['year']}):\\n"
        f"- Merchandise Exports : {ctx['exports_pct_gdp']}% of GDP\\n"
        f"- Merchandise Imports : {ctx['imports_pct_gdp']}% of GDP\\n"
        f"- Trade Balance       : {ctx['trade_balance_pct_gdp']}% of GDP\\n"
        f"- Crude Oil Benchmark : ${ctx['crude_price']}/barrel\\n\\n"
        "ARTICLE:\\n"
        f"Headline : {title}\\n"
        f"Category : {readable_class} / {channel}\\n"
        f"Content  : {article_content[:2000]}\\n\\n"
        "YOUR TASK:\\n"
        "Write exactly ONE concise phrase estimating the expected trade share impact on India.\\n"
        'Format: "~X% of [trade metric]; [brief impact in 4-6 words]"\\n\\n'
        "Examples of good answers:\\n"
        '- "~35% of India\'s crude import bill; upward CAD pressure likely"\\n'
        '- "Gold imports ~7% of total imports; mild rupee drag expected"\\n'
        '- "~22% of service export GDP; positive for BoP and rupee"\\n'
        '- "Minimal direct trade exposure; indirect inflation risk moderate"\\n\\n'
        "Return ONLY the phrase. No explanation. No JSON. No bullets."
    )

    try:
        resp2 = ollama.chat(model=OLLAMA_MODEL,
                            messages=[{'role': 'user', 'content': estimation_prompt}])
        raw  = resp2['message']['content'].strip()
        line = raw.split('\\n')[0].strip().strip('"\\' ').strip()
        if line:
            return f"EST:{line[:240]}"   # EST: prefix -> frontend shows disclaimer icon
    except Exception as exc:
        print(f"  [Trade Share S2] estimation failed: {exc}")

    return ''


# ====================== MAIN COMMAND'''

# Find and replace
start_idx = content.find(OLD_FUNC_START)
end_marker = "        return ''\n\n\n# ====================== MAIN COMMAND"
end_idx   = content.find(end_marker)

if start_idx == -1:
    print("ERROR: Could not find function start!")
elif end_idx == -1:
    print("ERROR: Could not find function end!")
else:
    new_content = content[:start_idx] + NEW_FUNC + content[end_idx + len(end_marker):]
    file_path.write_text(new_content, encoding='utf-8')
    print(f"SUCCESS: Replaced function ({end_idx - start_idx} chars -> {len(NEW_FUNC)} chars)")
    print(f"New file length: {len(new_content)} chars")
