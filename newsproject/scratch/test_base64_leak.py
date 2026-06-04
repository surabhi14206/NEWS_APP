import os
import sys
import django

# Setup Django settings context
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.spacy_utils import extract_locations_hybrid, clean_geotext

def main():
    title = "Coinbase offers trading using Indian rupee - Reuters"
    description = '<a href="https://news.google.com/rss/articles/CBMilAFBVV95cUxQaXRnNXJsRkFlT3hEMnZIMWMzQm01MEtXX2lZZ3MtQjRISjV6eHdXWW9FaHhBMjV2M3JTby15R0pPVTA4Z283ekJRVkpUbVJaUzhTMnE3S3VqWDBPQ040emw4UkduRVVhdDRJQnp2Z1JxdjJxblg0NDR2ekNiMHp2OGFwcGFBSkVWT0NJdG9VQTJqYk02?oc=5" target="_blank">Coinbase offers trading using Indian rupee</a>&nbsp;&nbsp;<font color="#6f6f6f">Reuters</font>'
    
    output_path = os.path.join(os.path.dirname(__file__), "test_base64_result.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("Original Description:\n")
        f.write(description + "\n\n")
        f.write("Cleaned Description via clean_geotext:\n")
        f.write(clean_geotext(description) + "\n\n")
        
        f.write("Running extract_locations_hybrid...\n")
        try:
            res = extract_locations_hybrid(
                title=title,
                description=description,
                full_text=description
            )
            import json
            f.write(json.dumps(res, indent=2))
        except Exception as e:
            f.write(f"Error: {e}\n")

if __name__ == '__main__':
    main()
