import os
import json
import subprocess
import sys
import ollama
from training import classify_single_item, run_evaluation, run_taxonomy_evaluation
import random


# Set console output encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Configuration
BASE_MODEL = "llama2:7b"
CUSTOM_MODEL_NAME = "news_filter_custom"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_SPLIT_PATH = os.path.join(DATA_DIR, "test_split.json")
TRAIN_SPLIT_PATH = os.path.join(DATA_DIR, "train_split.json")
MODELFILE_PATH = os.path.join(DATA_DIR, "Modelfile")

# Hardcoded high-quality representative examples for Ollama Modelfile
FEW_SHOT_EXAMPLES = [
    # 1. Irrelevant: Local tragedy
    {
        "input": {
            "title": "6-year-old girl dies while playing in Delhi's Holambi Khurd as old brick pillar collapses on her",
            "description": "No foul play has been reported in the incident so far as the police reached the site.",
            "event_class": "Domestic_Policy",
            "sub_type": "Infrastructure_Safety_and_Maintenance",
            "sector": "Infrastructure_Sector",
            "channel": "Low/No Macro Relevance",
            "insights": "Local tragedy involving collapsed brick pillar in Delhi.",
            "summary": "A young girl tragically died after a collapsed brick pillar in Holambi Khurd.",
            "direction": "negative",
            "origin": "Global"
        },
        "output": {
            "classification": "irrelevant",
            "reason": "Local tragedy/accident with no macroeconomic transmission channels or national policy impact."
        }
    },
    # 2. Irrelevant: Sports selection
    {
        "input": {
            "title": "Teenage sensation Sooryavanshi called up to India's T20I squad, Iyer named captain - Reuters",
            "description": "Teenage sensation Sooryavanshi called up to India's T20I squad, Iyer named captain",
            "event_class": "Consumer_Sentiment_and_Demand",
            "sub_type": "Consumer_Spending_and_Demand (Sports)",
            "sector": "Consumer_Goods_and_FMCG",
            "channel": "Low/No Macro Relevance (Sports)",
            "insights": "Cricket team selection and squad changes.",
            "summary": "Sooryavanshi selected for India T20I cricket squad under captain Iyer.",
            "direction": "positive",
            "origin": "India"
        },
        "output": {
            "classification": "irrelevant",
            "reason": "Sports news focusing on player selection and team composition with no macroeconomic impact."
        }
    },
    # 3. Irrelevant: Local crime/Individual event
    {
        "input": {
            "title": "28-year-old Indian man shot dead in US during pizza delivery: Cop",
            "description": "Preliminary findings suggest that the pizza order may have been placed for a vacant apartment.",
            "event_class": "Geo_Political",
            "sub_type": "International_Security_and_Risk (Indian Citizens Abroad)",
            "sector": "Banking_and_Finance",
            "channel": "Low/No Macro Relevance",
            "insights": "Tragic death of an Indian citizen in the United States.",
            "summary": "An Indian student from Telangana was shot dead during a delivery in the US.",
            "direction": "negative",
            "origin": "US"
        },
        "output": {
            "classification": "irrelevant",
            "reason": "Individual localized crime event affecting a citizen abroad, not impacting trade or national economies."
        }
    },
    # 4. Relevant: Trade policy / Competitor tariff
    {
        "input": {
            "title": "Sri Lanka has reduced the export tariff on IT Services",
            "description": "Due to decrease in tariff India is facing issues in its major tech cities like Bangalore and Hyderabad.",
            "event_class": "Trade_Policy",
            "sub_type": "Tariff_change (Tariff Reduction)",
            "sector": "IT_and_ITeS_Sector",
            "channel": "Trade competitiveness & Services Exports & Sectoral Employment",
            "insights": "Sri Lanka's tariff reduction directly increases competition for India's IT services, potentially leading to layoffs in tech hubs.",
            "summary": "Sri Lanka cuts export tariff on IT services, increasing competition for major Indian tech hubs.",
            "direction": "negative",
            "origin": "India"
        },
        "output": {
            "classification": "relevant",
            "reason": ""
        }
    },
    # 5. Relevant: Global oil shock
    {
        "input": {
            "title": "Stocks Pressured by AI Selloff and Jump in Oil Prices",
            "description": "Global stocks pressured by a tech selloff and rising crude oil prices.",
            "event_class": "Financial_Market",
            "sub_type": "Market_Volatility (Stock Market, Crude Prices)",
            "sector": "Stock_Market_and_Capital_Markets",
            "channel": "Commodity prices (Oil) & Imported Inflation & INR Exchange Rate & Equity Spillover",
            "insights": "Rising oil prices worsen India's trade deficit and import bill, putting pressure on inflation and currency value.",
            "summary": "Global markets decline due to tech selloff and rising oil prices, impacting import-dependent economies like India.",
            "direction": "negative",
            "origin": "US"
        },
        "output": {
            "classification": "relevant",
            "reason": ""
        }
    },
    # 6. Relevant: Central Bank Policy
    {
        "input": {
            "title": "Goldman Sees Rupee Weakness Capped After Steps to Boost Inflows",
            "description": "The Indian rupee's slide may be nearing a floor after RBI measures to boost foreign inflows.",
            "event_class": "Financial_Market",
            "sub_type": "Currency_and_FX (Rupee Depreciation, Currency Intervention)",
            "sector": "Stock_Market_and_Capital_Markets",
            "channel": "Capital Inflows & INR Exchange Rate Stabilization & RBI Policy Measures",
            "insights": "RBI currency intervention stabilizes the rupee, helping manage import inflation and foreign capital confidence.",
            "summary": "Goldman Sachs predicts rupee stabilization following proactive steps by Indian authorities to attract capital.",
            "direction": "positive",
            "origin": "India"
        },
        "output": {
            "classification": "relevant",
            "reason": ""
        }
    }
]

CLASSIFIER_MODEL_NAME = "news_classifier_custom"
CLASSIFIER_MODELFILE_PATH = os.path.join(DATA_DIR, "Modelfile_classifier")

def create_ollama_modelfile():
    print("Generating Ollama Modelfile for relevance filtering...")
    
    modelfile_content = '''FROM llama2:7b

TEMPLATE """{{- range $i, $_ := .Messages }}
{{- if eq .Role "user" }}[INST] {{ .Content }} [/INST]
{{- else if eq .Role "assistant" }}{{ .Content }}
{{- end }}
{{- end }}"""

SYSTEM """You are an expert macroeconomic & financial news analyst for an India-focused dashboard.

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
- **Irrelevant**: Local accidents, crime, sports, entertainment, weather, non-economic politics.

### Importance Score Guide:
- 9-10: Major policy announcement, RBI rate decision, big global event affecting India, major trade agreement.
- 6-8 : Sector-specific news, company results affecting indices, moderate policy changes, commodity price shifts.
- 1-5 : Low or no macroeconomic transmission.

### Few-Shot Examples:

[INST] Please analyze this news article:

Title: 6-year-old girl dies while playing in Delhi's Holambi Khurd as old brick pillar collapses on her
Description: No foul play has been reported in the incident so far as the police reached the site. [/INST]
{"classification": "irrelevant", "importance_score": 2, "sentiment": "Negative", "reason": "Local accident with no macro or financial impact", "key_impact": "", "key_entities": []}

[INST] Please analyze this news article:

Title: Teenage sensation Sooryavanshi called up to India's T20I squad, Iyer named captain
Description: Teenage sensation Sooryavanshi called up to India's T20I squad, Iyer named captain [/INST]
{"classification": "irrelevant", "importance_score": 1, "sentiment": "Positive", "reason": "Sports news with no macroeconomic transmission", "key_impact": "", "key_entities": []}

[INST] Please analyze this news article:

Title: Sri Lanka has reduced the export tariff on IT Services
Description: Due to decrease in tariff India is facing issues in its major tech cities like Bangalore and Hyderabad. [/INST]
{"classification": "relevant", "importance_score": 7, "sentiment": "Negative", "reason": "", "key_impact": "Increased competition for Indian IT exports may hurt revenues and employment in Bangalore & Hyderabad.", "key_entities": ["IT Sector", "Bangalore", "Hyderabad"]}

[INST] Please analyze this news article:

Title: Stocks Pressured by AI Selloff and Jump in Oil Prices
Description: Global stocks pressured by a tech selloff and rising crude oil prices. [/INST]
{"classification": "relevant", "importance_score": 8, "sentiment": "Negative", "reason": "", "key_impact": "Rising oil prices will widen India's trade deficit and fuel imported inflation.", "key_entities": ["Oil Prices", "Stock Market", "INR"]}

[INST] Please analyze this news article:

Title: RBI Keeps Repo Rate Unchanged at 6.5%
Description: The Monetary Policy Committee decided to maintain the repo rate citing persistent inflation risks. [/INST]
{"classification": "relevant", "importance_score": 9, "sentiment": "Neutral", "reason": "", "key_impact": "Major RBI policy decision affecting borrowing costs, liquidity, credit growth and overall economic outlook.", "key_entities": ["RBI", "Repo Rate"]}

[INST] Please analyze this news article:

Title: Goldman Sees Rupee Weakness Capped After Steps to Boost Inflows
Description: The Indian rupee's slide may be nearing a floor after RBI measures to boost foreign inflows. [/INST]
{"classification": "relevant", "importance_score": 8, "sentiment": "Positive", "reason": "", "key_impact": "RBI actions help stabilize the rupee, supporting import costs and investor confidence.", "key_entities": ["RBI", "INR", "Foreign Inflows"]}

[INST] Please analyze this news article:

Title: US Imposes New Tariffs on Chinese EVs and Semiconductors
Description: Escalating trade tensions between US and China may create opportunities for Indian manufacturers. [/INST]
{"classification": "relevant", "importance_score": 7, "sentiment": "Positive", "reason": "", "key_impact": "May boost Indian electronics and auto component exports due to China+1 strategy.", "key_entities": ["Trade Policy", "Electronics", "Auto Sector"]}

[INST] Please analyze this news article:

Title: Heavy rains cause flooding in Mumbai suburbs
Description: Several low-lying areas reported waterlogging after heavy monsoon showers. [/INST]
{"classification": "irrelevant", "importance_score": 3, "sentiment": "Negative", "reason": "Local weather-related incident with no significant macro impact", "key_impact": "", "key_entities": []}"""

PARAMETER temperature 0.1
PARAMETER top_k 50
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
'''
    
    with open(MODELFILE_PATH, 'w', encoding='utf-8') as f:
        f.write(modelfile_content)
    
    print(f"Modelfile written to: {MODELFILE_PATH}")

def select_diverse_few_shot_examples(train_split_path, num_examples=6):
    try:
        with open(train_split_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []
        
    # Filter only relevant items
    relevant_items = [item for item in data if item.get('actual_label') == 'relevant']
    
    # Group by L1 event_class
    by_class = {}
    for item in relevant_items:
        ec = item.get('event_class')
        if ec:
            by_class.setdefault(ec, []).append(item)
            
    selected = []
    classes = list(by_class.keys())
    
    # Cycle through classes to select one from each until we reach num_examples
    idx = 0
    while len(selected) < num_examples and classes:
        cls = classes[idx % len(classes)]
        if by_class[cls]:
            item = by_class[cls].pop(0)
            selected.append(item)
        else:
            classes.remove(cls)
        idx += 1
        
    return selected

def create_classifier_modelfile(train_split_path, classifier_modelfile_path):
    print("Generating Ollama Classifier Modelfile...")
    
    system_prompt = """You are an expert financial and macroeconomic analyst.
Your task is to classify news articles into their correct Event Class (L1), Sector, Sub-type (L2), and Transmission Channel based on India's economy and global macroeconomics.

EVENT CLASSES (L1) and Sub-types (L2):
- Domestic_Policy: Fiscal_Policy, Monetary_RBI_Policy, Regulatory_and_Sectoral_Reforms, Taxation_and_Revenue, Infrastructure_and_Capex, Banking_and_Financial_Sector_Reforms, Social_and_Welfare_Policy, Economic_Reforms_and_Growth, Policy_Uncertainty_and_Risk, GST_Revision
- Climate_and_Natural: Weather_Extremes, Drought_and_Monsoon, Food_and_Agriculture_Crisis, Natural_Disasters, Water_Resources, Economic_Impact, Government_and_Policy_Response, Climate_Change_Longterm, Commodity_Linkages, Sectoral_Impact, El_Nino/La_Nina
- Financial_Market: Market_Volatility, Banking_and_Liquidity, Global_Financial, Equity_Markets, Fixed_Income_and_Debt, Currency_and_FX, Commodity_Linkage, Regulatory_and_Policy, Systemic_Risk, Alternative_Investments, Market_Structure, Sentiment_and_Positioning, Dollar_Surge
- Commodity_Shock: Energy_and_Crude_Oil, Metals_and_Minerals, Food_and_Agriculture, Fertiliser_Stocks, Natural_Gas, Supply_Chain_and_Geopolitics, Transportation_and_Logistics, Commodity_Markets_and_Trading, Inflation_and_Macro_Linkage, Alternative_and_Emerging_Commodities, Risk_and_Sentiment
- Geo_Political: Geopolitical_Events, Regional_Conflicts, Armed_Conflicts, Sanctions, Alliance_shift, Border_dispute, Terror_Event, USD_RISK, Dipl_Rupture, Major_Powers, Political_Risk
- Trade_Policy: Trade_Tensions_and_Tariffs, Export_Promotion_and_Schemes, Trade_Agreements_FTAs, FDI_and_FPI_Inflows, Foreign_Trade_Regulations, Special_Economic_Zones, Export_Import_Trends, Trade_Barriers, Global_Trade_Alliances, Competitiveness_Indicators, Customs_and_Duties, Trade_Infrastructure, Service_Exports
- Global_Factors: Global_Economy, Global_Central_Banks, Global_Inflation, Global_Supply_Chain, Global_Risk, Global_Currency, Global_Trade, Global_Growth, Global_Commodity
- Inflation_and_Pricing: Inflation_Indicators, Price_Volatility, Cost_Push_Inflation, Demand_Pull_Inflation, Core_Inflation, Headline_Inflation, Wholesale_Prices, Retail_Prices, Pricing_Power, Price_Control, Inflation_Expectations
- Consumer_Sentiment_and_Demand: Consumer_Spending, Retail_Sales, Private_Consumption, Consumer_Confidence, Business_Sentiment, Discretionary_Spending, Essential_Spending, Premiumisation, Downtrading, Festive_Demand, Consumer_Credit
- Macro_Economy: GDP_Growth, Industrial_Production, Services_Growth, Economic_Outlook, Growth_Forecast, Economic_Indicator, Growth_Sectors, Structural_Growth, Macro_Stability, Economic_Survey, NITI_Aayog

SECTORS:
Choose from: Banking_and_Finance, Stock_Market_and_Capital_Markets, Manufacturing_Sector, IT_and_ITeS_Sector, Information_Technology_AIML_DS, Infrastructure_Sector, Oil_Gas_and_Refining, Cement_and_Construction_Materials, Gems_and_Jewellery, Media_and_Entertainment, Fertilizers_and_Agrochemicals, Paper_and_Packaging, Water_and_Sanitation, ESG_and_Sustainability, Foreign_Trade_and_Exports, Energy_and_Power_Sector, Automobile_and_Auto_Components, Agriculture_and_Allied_Sectors, Real_Estate_and_Construction, Pharmaceuticals_and_Healthcare, Consumer_Goods_and_FMCG, Metals_and_Mining, Logistics_and_Transportation, Telecom_and_Digital_Economy, Insurance_Sector, Aviation_and_Airlines, Tourism_and_Hospitality, Education_Sector, Chemicals_and_Petrochemicals, Defense_and_Aerospace, Textiles_and_Apparel, Retail_and_Ecommerce, Startups_and_Venture_Capital, Railways_Sector, Electronics_and_Semiconductor, Food_Processing_Industry, Biotechnology_and_Life_Sciences, Steel_and_Heavy_Industries, Mutual_Funds_and_Asset_Management, Space_and_Defence_Tech, Rural_Economy_and_MGNREGA, Power_Transmission_and_Distribution, Gaming_and_Esports, Shipping_and_Ports, Consumer_Durables, Tyre_Industry, Paint_and_Coating, Housing_Finance_Companies, Pension_Sector, EV_Battery_and_Lithium, Drone_Industry, Leather_and_Footwear, Fisheries_and_Aquaculture, Cables_and_Wires, Plastics_and_Petrochemical_Products, Auto_Ancillary_and_Components, Handicrafts_and_Carpets, Renewable_Energy_Equipment, Pharmaceutical_Ingredients_API, Telecom_Equipment_and_Infrastructure, Aviation_MRO, Forestry_and_Paper_Products, Healthcare_Equipment_and_Medical_Devices, Electric_Vehicle_Charging, Microfinance_and_NBFC_MFI, Nuclear_Energy_and_Atomic_Sector, Waste_Management_and_Recycling, Luxury_Goods_and_Apparel, Cold_Chain_and_Warehousing, Credit_Rating_Agencies, Commodity_Trading_and_Exchanges, General / Macro.

INSTRUCTIONS:
1. Classify the article into one Event Class (L1) and one Sector.
2. Select the most specific L2 Sub-type under the selected L1. Find 1-2 keywords/phrases from the article that match the taxonomy and format it as: "L2_Key (Keyword1, Keyword2)".
3. Formulate the "channel" describing how the impact travels to the economy.
4. Output ONLY a valid JSON object. Do not output any other text or explanation.

JSON format:
{
  "event_class": "L1_Key",
  "sector": "Sector_Key",
  "sub_type": "L2_Key (Keyword1, Keyword2)",
  "channel": "Channel text"
}"""

    modelfile_lines = [
        f"FROM {BASE_MODEL}",
        "PARAMETER temperature 0.0",
        f"SYSTEM \"\"\"{system_prompt}\"\"\""
    ]

    examples = select_diverse_few_shot_examples(train_split_path, num_examples=8)
    for ex in examples:
        input_str = f"Please classify the following news article:\n\n" \
                    f"Title: {ex.get('title')}\n" \
                    f"Description: {ex.get('description')}"
                    
        output_obj = {
            "event_class": ex.get("event_class"),
            "sector": ex.get("sector"),
            "sub_type": ex.get("sub_type"),
            "channel": ex.get("channel")
        }
        output_str = json.dumps(output_obj, ensure_ascii=False)
        
        modelfile_lines.append(f"MESSAGE user \"\"\"{input_str}\"\"\"")
        modelfile_lines.append(f"MESSAGE assistant \"\"\"{output_str}\"\"\"")

    modelfile_content = "\n\n".join(modelfile_lines)
    
    with open(classifier_modelfile_path, 'w', encoding='utf-8') as f:
        f.write(modelfile_content)
    
    print(f"Classifier Modelfile written to: {classifier_modelfile_path}")

def build_custom_ollama_model(model_name, modelfile_path):
    print(f"Creating custom model '{model_name}' in Ollama...")
    try:
        with open(modelfile_path, 'r', encoding='utf-8') as f:
            modelfile_content = f.read()
            
        print("Registering custom model via Ollama API...")
        response = ollama.create(
            model=model_name,
            modelfile=modelfile_content
        )
        print("Ollama Response:", response)
        print(f"Custom model '{model_name}' created successfully!")
        return True
    except Exception as e:
        print("Error creating custom model via SDK:", e)
        print("Attempting command line fallback...")
        try:
            cmd = f"ollama create {model_name} -f \"{modelfile_path}\""
            subprocess.run(cmd, shell=True, check=True)
            print(f"Custom model '{model_name}' created successfully via command line!")
            return True
        except Exception as se:
            print("Command line fallback failed:", se)
            return False

def print_comparison(pre_metrics, post_metrics):
    print("\n" + "="*50)
    print("          RELEVANCE PERFORMANCE COMPARISON          ")
    print("="*50)
    print(f"{'Metric':<25} | {'Base Model':<10} | {'Custom Model':<10}")
    print("-"*50)
    print(f"{'Overall Accuracy':<25} | {pre_metrics['accuracy']:.4f}     | {post_metrics['accuracy']:.4f}")
    print(f"{'Relevant Precision':<25} | {pre_metrics['precision_rel']:.4f}     | {post_metrics['precision_rel']:.4f}")
    print(f"{'Relevant Recall':<25} | {pre_metrics['recall_rel']:.4f}     | {post_metrics['recall_rel']:.4f}")
    print(f"{'Relevant F1-Score':<25} | {pre_metrics['f1_rel']:.4f}     | {post_metrics['f1_rel']:.4f}")
    print(f"{'Irrelevant Precision':<25} | {pre_metrics['precision_irrel']:.4f}     | {post_metrics['precision_irrel']:.4f}")
    print(f"{'Irrelevant Recall':<25} | {pre_metrics['recall_irrel']:.4f}     | {post_metrics['recall_irrel']:.4f}")
    print(f"{'Irrelevant F1-Score':<25} | {pre_metrics['f1_irrel']:.4f}     | {post_metrics['f1_irrel']:.4f}")
    print(f"{'Irrelevant Count Filtered':<25} | {pre_metrics['no_use_count']:<10} | {post_metrics['no_use_count']:<10}")
    print("="*50 + "\n")

def print_taxonomy_comparison(pre_tax_metrics, post_tax_metrics):
    print("\n" + "="*60)
    print("          TAXONOMY PERFORMANCE COMPARISON          ")
    print("="*60)
    print(f"{'Metric':<30} | {'Base Model':<10} | {'Custom Model':<10}")
    print("-"*60)
    print(f"{'Event Class (L1) Accuracy':<30} | {pre_tax_metrics['l1_accuracy']:.4f}     | {post_tax_metrics['l1_accuracy']:.4f}")
    print(f"{'Sector Accuracy':<30} | {pre_tax_metrics['sector_accuracy']:.4f}     | {post_tax_metrics['sector_accuracy']:.4f}")
    print(f"{'Sub-type (L2) Accuracy':<30} | {pre_tax_metrics['l2_accuracy']:.4f}     | {post_tax_metrics['l2_accuracy']:.4f}")
    print("="*60 + "\n")

def run_hf_qlora_training():
    pass

if __name__ == "__main__":
    # Ensure test split exists
    if not os.path.exists(TEST_SPLIT_PATH):
        print(f"[ERROR] Test split not found at {TEST_SPLIT_PATH}. Please run training.py first to create the splits.")
        sys.exit(1)
        
    with open(TEST_SPLIT_PATH, 'r', encoding='utf-8') as f:
        test_set = json.load(f)

    # 1. Evaluate base model (Pre-fine-tuning evaluation)
    print("Evaluating base model gemma3:4b before training/fine-tuning...")
    pre_metrics = run_evaluation(BASE_MODEL, test_set, limit=30)
    pre_tax_metrics = run_taxonomy_evaluation(BASE_MODEL, test_set, limit=20)

    # 2. Generate Modelfiles for Ollama
    create_ollama_modelfile()
    create_classifier_modelfile(TRAIN_SPLIT_PATH, CLASSIFIER_MODELFILE_PATH)

    # 3. Compile custom models in Ollama
    success_filter = build_custom_ollama_model(CUSTOM_MODEL_NAME, MODELFILE_PATH)
    success_classifier = build_custom_ollama_model(CLASSIFIER_MODEL_NAME, CLASSIFIER_MODELFILE_PATH)
    
    if not success_filter or not success_classifier:
        print("[ERROR] Failed to create custom models in Ollama. Exiting.")
        sys.exit(1)

    # 4. Evaluate custom models (Post-fine-tuning evaluation)
    print("\nEvaluating custom models after training/fine-tuning...")
    post_metrics = run_evaluation(CUSTOM_MODEL_NAME, test_set, limit=30)
    post_tax_metrics = run_taxonomy_evaluation(CLASSIFIER_MODEL_NAME, test_set, limit=20)

    # 5. Print comparison tables
    print_comparison(pre_metrics, post_metrics)
    print_taxonomy_comparison(pre_tax_metrics, post_tax_metrics)

