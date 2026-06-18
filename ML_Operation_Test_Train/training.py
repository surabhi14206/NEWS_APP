import os
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import ollama

# Set console output encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Configuration
BASE_MODEL = "llama2:7b"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIN_DATA_PATH = os.path.join(DATA_DIR, "training_data.json")
LOW_IMPACT_PATH = os.path.join(DATA_DIR, "low_impact_events.json")
TRAIN_SPLIT_PATH = os.path.join(DATA_DIR, "train_split.json")
TEST_SPLIT_PATH = os.path.join(DATA_DIR, "test_split.json")
NO_USE_DATA_PATH = os.path.join(DATA_DIR, "no_use_data.json")

SYSTEM_PROMPT = """You are an expert macroeconomic & financial news analyst for an India-focused dashboard.

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
}"""

def make_user_prompt(item):
    return f"""Please classify the following news article:

Title: {item.get('title')}
Description: {item.get('description')}
Event Class: {item.get('event_class')}
Sub Type: {item.get('sub_type')}
Sector: {item.get('sector')}
Channel: {item.get('channel')}
Insights: {item.get('insights')}
Summary: {item.get('summary')}
Direction: {item.get('direction')}
Origin: {item.get('origin')}"""

def load_and_split_data():
    print("Loading datasets...")
    with open(TRAIN_DATA_PATH, 'r', encoding='utf-8') as f:
        train_data = json.load(f)
    with open(LOW_IMPACT_PATH, 'r', encoding='utf-8') as f:
        low_impact = json.load(f)

    # Compile set of titles from low_impact_events.json (irrelevant data)
    irrelevant_titles = set(item['title'].strip() for item in low_impact)

    processed_data = []
    
    # Process items in training_data.json
    for item in train_data:
        title = item.get('title', '').strip()
        channel = str(item.get('channel', ''))
        
        # Rule: channel contains 'Low/No Macro' or title matches low_impact_events => irrelevant
        if 'Low/No Macro' in channel or title in irrelevant_titles:
            label = "irrelevant"
        else:
            label = "relevant"
            
        processed_data.append({
            'title': item.get('title', ''),
            'description': item.get('description', ''),
            'event_class': item.get('event_class', ''),
            'sub_type': item.get('sub_type', ''),
            'sector': item.get('sector', ''),
            'channel': item.get('channel', ''),
            'insights': item.get('insights', ''),
            'summary': item.get('summary', ''),
            'direction': item.get('direction', ''),
            'origin': item.get('origin', ''),
            'actual_label': label
        })

    # Add items from low_impact_events that are not in training_data
    train_titles = set(item.get('title', '').strip() for item in train_data)
    for item in low_impact:
        title = item.get('title', '').strip()
        if title not in train_titles:
            processed_data.append({
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'event_class': item.get('event_class', ''),
                'sub_type': item.get('sub_type', ''),
                'sector': item.get('sector', ''),
                'channel': item.get('channel', ''),
                'insights': item.get('insights', ''),
                'summary': item.get('summary', ''),
                'direction': item.get('direction', ''),
                'origin': item.get('origin', ''),
                'actual_label': 'irrelevant'
            })

    # Shuffle and split
    random.seed(42)
    random.shuffle(processed_data)

    split_idx = int(len(processed_data) * 0.8)
    train_set = processed_data[:split_idx]
    test_set = processed_data[split_idx:]

    print(f"Total dataset: {len(processed_data)} items")
    print(f"Training split: {len(train_set)} items")
    print(f"Testing split: {len(test_set)} items")

    # Save to disk
    with open(TRAIN_SPLIT_PATH, 'w', encoding='utf-8') as f:
        json.dump(train_set, f, indent=2, ensure_ascii=False)
    with open(TEST_SPLIT_PATH, 'w', encoding='utf-8') as f:
        json.dump(test_set, f, indent=2, ensure_ascii=False)
    
    print("Splits successfully saved to train_split.json and test_split.json.")
    return train_set, test_set

def classify_single_item(model, item):
    user_prompt = make_user_prompt(item)
    try:
        response = ollama.chat(
            model=model,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': user_prompt}
            ],
            format='json',
            options={'temperature': 0.0} # Use temperature 0.0 for deterministic classification
        )
        content = response['message']['content']
        result = json.loads(content)
        return {
            'item': item,
            'predicted_label': result.get('classification', 'relevant').lower().strip(),
            'reason': result.get('reason', '').strip(),
            'error': None
        }
    except Exception as e:
        return {
            'item': item,
            'predicted_label': 'error',
            'reason': str(e),
            'error': str(e)
        }

def run_evaluation(model_name, test_set, limit=50):
    print(f"\n--- Running Evaluation using Model: {model_name} ---")
    
    # If limit is specified, evaluate on a subset for speed, but keep track of it
    if limit and len(test_set) > limit:
        print(f"Evaluating on a random subset of {limit} items out of {len(test_set)} to save time.")
        random.seed(42)
        eval_set = random.sample(test_set, limit)
    else:
        eval_set = test_set
        print(f"Evaluating on all {len(eval_set)} items.")

    results = []
    no_use_data = []

    # Use ThreadPoolExecutor for concurrent querying of local Ollama model
    # (Max 3 threads to prevent overloading local GPU / CPU)
    print("Sending queries to Ollama...")
    completed_count = 0
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(classify_single_item, model_name, item): item for item in eval_set}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed_count += 1
            if completed_count % 10 == 0 or completed_count == len(eval_set):
                print(f"Progress: {completed_count}/{len(eval_set)} processed.")

    # Calculate metrics
    tp, tn, fp, fn = 0, 0, 0, 0
    errors = 0
    
    for res in results:
        actual = res['item']['actual_label']
        predicted = res['predicted_label']
        
        if predicted == 'error':
            errors += 1
            continue
            
        if actual == 'relevant' and predicted == 'relevant':
            tp += 1
        elif actual == 'irrelevant' and predicted == 'irrelevant':
            tn += 1
        elif actual == 'irrelevant' and predicted == 'relevant':
            fp += 1
        elif actual == 'relevant' and predicted == 'irrelevant':
            fn += 1

        # If predicted as irrelevant, put into the "no use data"
        if predicted == 'irrelevant':
            no_use_data.append({
                'title': res['item']['title'],
                'description': res['item']['description'],
                'reason_why_no_use': res['reason'] if res['reason'] else "Identified as irrelevant local/non-macro incident."
            })

    # Save irrelevant news to no_use_data.json
    with open(NO_USE_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(no_use_data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(no_use_data)} predicted irrelevant news to no_use_data.json")

    # Metrics computation
    total_valid = tp + tn + fp + fn
    accuracy = (tp + tn) / total_valid if total_valid > 0 else 0
    
    # Precision, Recall, F1 for Relevant (Positive class)
    precision_rel = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall_rel = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_rel = 2 * precision_rel * recall_rel / (precision_rel + recall_rel) if (precision_rel + recall_rel) > 0 else 0

    # Precision, Recall, F1 for Irrelevant (Negative class)
    precision_irrel = tn / (tn + fn) if (tn + fn) > 0 else 0
    recall_irrel = tn / (tn + fp) if (tn + fp) > 0 else 0
    f1_irrel = 2 * precision_irrel * recall_irrel / (precision_irrel + recall_irrel) if (precision_irrel + recall_irrel) > 0 else 0

    print("\n================ EVALUATION RESULTS ================")
    print(f"Model Evaluated: {model_name}")
    print(f"Total evaluated items: {total_valid} (Errors: {errors})")
    print(f"Accuracy: {accuracy:.4f} ({tp+tn}/{total_valid})")
    print("\n--- Class: Relevant (Macro-Economic Value) ---")
    print(f"Precision: {precision_rel:.4f}")
    print(f"Recall:    {recall_rel:.4f}")
    print(f"F1-Score:  {f1_rel:.4f}")
    print("\n--- Class: Irrelevant (No Use Data) ---")
    print(f"Precision: {precision_irrel:.4f}")
    print(f"Recall:    {recall_irrel:.4f}")
    print(f"F1-Score:  {f1_irrel:.4f}")
    print("====================================================\n")

    return {
        'accuracy': accuracy,
        'precision_rel': precision_rel,
        'recall_rel': recall_rel,
        'f1_rel': f1_rel,
        'precision_irrel': precision_irrel,
        'recall_irrel': recall_irrel,
        'f1_irrel': f1_irrel,
        'no_use_count': len(no_use_data)
    }

def classify_taxonomy_single_item(model, item):
    user_prompt = f"""Please classify the following news article:

Title: {item.get('title')}
Description: {item.get('description')}"""
    
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
    try:
        response = ollama.chat(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            format='json',
            options={'temperature': 0.0}
        )
        content = response['message']['content']
        result = json.loads(content)
        return {
            'item': item,
            'predicted': {
                'event_class': result.get('event_class', '').strip(),
                'sector': result.get('sector', '').strip(),
                'sub_type': result.get('sub_type', '').strip(),
                'channel': result.get('channel', '').strip()
            },
            'error': None
        }
    except Exception as e:
        return {
            'item': item,
            'predicted': {},
            'error': str(e)
        }

def run_taxonomy_evaluation(model_name, test_set, limit=50):
    print(f"\n--- Running Taxonomy Evaluation using Model: {model_name} ---")
    
    # Filter test_set to only contain relevant articles
    eval_set = [item for item in test_set if item.get('actual_label') == 'relevant']
    if not eval_set:
        eval_set = test_set
        
    if limit and len(eval_set) > limit:
        print(f"Evaluating taxonomy on a subset of {limit} items out of {len(eval_set)}.")
        random.seed(42)
        eval_set = random.sample(eval_set, limit)
    else:
        print(f"Evaluating taxonomy on all {len(eval_set)} items.")

    results = []
    completed_count = 0
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(classify_taxonomy_single_item, model_name, item): item for item in eval_set}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed_count += 1
            if completed_count % 10 == 0 or completed_count == len(eval_set):
                print(f"Progress: {completed_count}/{len(eval_set)} processed.")

    def clean_eval_str(s: str) -> str:
        return s.lower().replace('_', '').replace(' ', '').replace('&', 'and').replace('/', 'and').strip()

    correct_l1 = 0
    correct_sector = 0
    correct_l2 = 0
    errors = 0
    total = 0

    for res in results:
        if res['error']:
            errors += 1
            continue
            
        total += 1
        item = res['item']
        pred = res['predicted']

        act_l1 = item.get('event_class', '')
        act_sector = item.get('sector', '')
        act_l2_full = item.get('sub_type', '')
        act_l2 = act_l2_full.split('(')[0].strip()

        pred_l1 = pred.get('event_class', '')
        pred_sector = pred.get('sector', '')
        pred_l2_full = pred.get('sub_type', '')
        pred_l2 = pred_l2_full.split('(')[0].strip()

        if clean_eval_str(act_l1) == clean_eval_str(pred_l1):
            correct_l1 += 1
        if clean_eval_str(act_sector) == clean_eval_str(pred_sector):
            correct_sector += 1
        if clean_eval_str(act_l2) == clean_eval_str(pred_l2):
            correct_l2 += 1

    l1_acc = correct_l1 / total if total > 0 else 0
    sector_acc = correct_sector / total if total > 0 else 0
    l2_acc = correct_l2 / total if total > 0 else 0

    print("\n================ TAXONOMY EVALUATION RESULTS ================")
    print(f"Model: {model_name}")
    print(f"Total evaluated items: {total} (Errors: {errors})")
    print(f"Event Class (L1) Accuracy: {l1_acc:.4f} ({correct_l1}/{total})")
    print(f"Sector Accuracy:            {sector_acc:.4f} ({correct_sector}/{total})")
    print(f"Sub-type (L2) Accuracy:     {l2_acc:.4f} ({correct_l2}/{total})")
    print("==============================================================\n")

    return {
        'l1_accuracy': l1_acc,
        'sector_accuracy': sector_acc,
        'l2_accuracy': l2_acc,
        'total': total,
        'errors': errors
    }

if __name__ == "__main__":
    # Load and split datasets if train/test split files do not exist yet
    if not os.path.exists(TRAIN_SPLIT_PATH) or not os.path.exists(TEST_SPLIT_PATH):
        train_set, test_set = load_and_split_data()
    else:
        print("Loading existing split files...")
        with open(TRAIN_SPLIT_PATH, 'r', encoding='utf-8') as f:
            train_set = json.load(f)
        with open(TEST_SPLIT_PATH, 'r', encoding='utf-8') as f:
            test_set = json.load(f)
        print(f"Loaded train set: {len(train_set)} items, test set: {len(test_set)} items")

    # Evaluate base model (Gemma 3: 4B)
    run_evaluation(BASE_MODEL, test_set, limit=None)
    run_taxonomy_evaluation(BASE_MODEL, test_set, limit=30)

