import os
import sys
import json
import django

# Setup Django settings context
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.spacy_utils import extract_locations_hybrid

def test_spacy_extraction():
    test_articles = [
        {
            "title": "Delhi High Court on Monday dismissed a petition seeking to stop the construction of a new airport in Jewar, Uttar Pradesh.",
            "description": "The project is expected to boost connectivity in the National Capital Region.",
            "full_text": "The long-planned Jewar airport in Gautam Buddha Nagar county, Uttar Pradesh, has cleared its final legal obstacle as the High Court in New Delhi rejected a challenge. Officials in Lucknow and Mumbai welcomed the decision, which is expected to attract major business from US and China."
        },
        {
            "title": "New protests erupt in Tehran over economic challenges",
            "description": "Demonstrators gathered in parts of the Iranian capital calling for reforms.",
            "full_text": "Several rallies were reported across Tehran district and surrounding locations in Iran as economic concerns mount. Similar demonstrations have occurred in Isfahan and Shiraz."
        }
    ]

    print("=" * 80)
    print("RUNNING SPACY + OLLAMA HYBRID NER TESTS")
    print("=" * 80)

    for idx, article in enumerate(test_articles, 1):
        print(f"\n[Test Case {idx}]")
        print(f"Title: {article['title']}")
        
        try:
            res = extract_locations_hybrid(
                title=article['title'],
                description=article['description'],
                full_text=article['full_text']
            )
            print("\nExtracted Data:")
            print(json.dumps(res, indent=2))
        except Exception as e:
            print(f"Error during extraction: {e}")
            
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_spacy_extraction()
