import json
import os

log_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\newsfeeds_scrape_log.json"
if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8') as f:
        # Load only a part or head if it's large, but let's try to load it first
        try:
            data = json.load(f)
            print("Log file type:", type(data))
            if isinstance(data, dict):
                print("Root keys:", list(data.keys()))
                for k in list(data.keys())[:5]:
                    val = data[k]
                    print(f"Key '{k}': type={type(val)}")
                    if isinstance(val, list) and val:
                        print(f"  List length: {len(val)}")
                        print(f"  First element keys/type: {type(val[0])}")
                        if isinstance(val[0], dict):
                            print(f"  First element sample: {list(val[0].keys())}")
                            # Print a step sample if exists
                            if "steps" in val[0]:
                                print(f"  Steps for first element: {val[0]['steps']}")
            elif isinstance(data, list):
                print("List length:", len(data))
                if data:
                    print("First element keys:", list(data[0].keys()) if isinstance(data[0], dict) else type(data[0]))
        except Exception as e:
            print("Error loading JSON:", e)
else:
    print("Log file does not exist")
