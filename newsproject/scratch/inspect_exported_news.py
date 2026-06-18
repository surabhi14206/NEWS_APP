import json
import os

exported_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\exported_news.json"
if os.path.exists(exported_path):
    with open(exported_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("Exported news type:", type(data))
    if isinstance(data, list):
        print("Exported news count:", len(data))
        if data:
            print("First item:", data[0])
    elif isinstance(data, dict):
        print("Keys:", data.keys())
else:
    print("exported_news.json does not exist")
