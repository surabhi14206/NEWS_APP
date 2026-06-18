import ollama
import json

INSTRUCTIONS = """You are an expert macroeconomic & financial news analyst for an India-focused dashboard.

Classify news articles as "relevant" or "irrelevant" and provide detailed analysis.
Always respond with **ONLY valid JSON** — no extra text.

JSON Format:
{
  "classification": "relevant" | "irrelevant",
  "importance_score": 1-10,
  "sentiment": "Positive" | "Negative" | "Neutral",
  "reason": "Brief reason only if irrelevant, otherwise empty string",
  "key_impact": "One sentence describing macroeconomic or financial impact on India/markets",
  "key_entities": ["RBI", "IT Sector", "INR", ...]
}

### Classification Rules:
- **Relevant**: Impacts economy, markets, RBI/Fed policy, trade, currency (INR), inflation, key sectors (IT, Banking, Oil/Energy, Metals, Textiles, Pharma, Auto).
- **Irrelevant**: Local accidents, crime, sports, entertainment, weather, non-economic politics, military uniform changes/dress codes, administrative changes, or national symbols.

### Few-Shot Examples:

Article:
Title: Indian Army drops colonial-era dress traditions, introduces bandi jackets in new uniform code
Description: The regulations permit women officers to wear sober-coloured sarees, or kurta-salwar and ankle-length straight pants with a dupatta.
Analysis:
{"classification": "irrelevant", "importance_score": 1, "sentiment": "Neutral", "reason": "Military dress code update with no macroeconomic transmission or fiscal impact.", "key_impact": "", "key_entities": []}

Article:
Title: Stocks Pressured by AI Selloff and Jump in Oil Prices
Description: Global stocks pressured by a tech selloff and rising crude oil prices.
Analysis:
{"classification": "relevant", "importance_score": 8, "sentiment": "Negative", "reason": "", "key_impact": "Rising oil prices will widen India's trade deficit and fuel imported inflation.", "key_entities": ["Oil Prices", "Stock Market", "INR"]}"""

title = "Indian Army drops colonial-era dress traditions, introduces bandi jackets in new uniform code"
desc = "The regulations permit women officers to wear sober-coloured sarees, or kurta-salwar and ankle-length straight pants with a dupatta."

combined_prompt = f"{INSTRUCTIONS}\n\nArticle:\nTitle: {title}\nDescription: {desc}\nAnalysis:"

print("Running test with clean few-shot examples:")
try:
    response = ollama.chat(
        model='news_filter_custom:latest',
        messages=[
            {'role': 'user', 'content': combined_prompt}
        ],
        format='json',
        options={'temperature': 0.0}
    )
    print("Response:")
    print(response['message']['content'])
except Exception as e:
    print("Error:", e)
